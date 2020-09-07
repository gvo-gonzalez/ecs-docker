#!/usr/bin/env python
import glob
import json
import os
import sys
import git
import time
import subprocess
import re
import boto3
import base64
import docker
import shutil
import urllib, http, logging
from shutil import copyfile
from subprocess import Popen, PIPE, check_output
from git import RemoteProgress
from subprocess import check_call
from urllib.request import urlopen

class CloneProgress(RemoteProgress):
    def update(
        self, 
        op_code, 
        cur_count, 
        max_count=None, 
        message=''
    ):
        if message:
            print(message)

def gitCloneSrcCode(from_repo, to_local_dir):
    printStep("Cloning project: " + from_repo + ' into folder: ' + to_local_dir)
    if not os.path.isdir(to_local_dir):
        try:
            os.makedirs(to_local_dir)
            git.Repo.clone_from(from_repo, to_local_dir, branch='master', progress=CloneProgress() )
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    if not os.path.isdir(to_local_dir + '/.git') or (to_local_dir == ""):
        shutil.rmtree(to_local_dir)
        git.Repo.clone_from(from_repo, to_local_dir, branch='master', progress=CloneProgress() )
    else: 
        print ("- Project source code seems cloned on: " + to_local_dir + "\n\n")

    printFinihedStep("Clone Completed")

def gitGetVersion(repoCloned):
    repo_url = repoCloned
    process = subprocess.Popen(["git", "ls-remote", repo_url], stdout=subprocess.PIPE)
    stdout, stderr = process.communicate()
    sha = re.split(r'\t+', stdout.decode('ascii'))[0]
    
    return sha[0:7]

def printStep(messagge):
    messaggeLen     = len(messagge) + 10
    print ("-" * messaggeLen)
    print ("|    " + messagge + "    |")
    print ("-" * messaggeLen + "\n") 

def printFinihedStep(messagge):
    messaggeLen     = len(messagge) + 10
    print ("|==>    " + messagge + "  <==|")

def getConfigInfo(configFile):
    
    printStep("Parse Config File: " + configFile )
    fileDetails    = None
    try:
        with open(configFile) as config:
            fileDetails = json.load(config)
    except Exception as e:
        print ("Error while parsing config file", e)
        sys.exit(1)

    appsDetails  = fileDetails['appLayer'] if "appLayer" in fileDetails else [] 
    dbDetails    = fileDetails['backendLayer'] if "backendLayer" in fileDetails else []
    customInfo   = fileDetails['custom'] if "custom" in fileDetails else []
    
    printFinihedStep("DONE Parse Configuration File")

    return fileDetails['projectName'], appsDetails, dbDetails, customInfo

def createDockerFie(
    fullScriptPath, 
    appName, 
    domainToUse, 
    projectPath, 
    framework
):
    frontEndNginx = ""        
    src = fullScriptPath + '/nginx/templates/' + "vhost.{}.template".format(framework)
    dst = fullScriptPath + '/nginx/' + appName + ".conf"
    copyfile(src, dst)

    sed_vhost = "sed -i.bak 's/{{ %s }}/%s/g' %s"
    os.system(sed_vhost % ("servernames", domainToUse, dst)) 
    os.system(sed_vhost % ("backend", appName, dst))

    # Create Custom Dockerfile for NGINX server
    file_object = open(fullScriptPath + '/nginx/Dockerfile.' + framework, 'w')
    file_object.write('FROM nginx:stable-alpine\n\n')
    if framework == 'laravel':
        file_object.write('RUN mkdir -p /var/www/public\n\n')
        file_object.write('COPY ' + projectPath + '/public /var/www/public\n\n')
        file_object.write('COPY nginx/' + appName + '.conf /etc/nginx/conf.d/default.conf\n')
        file_object.close()
        frontEndNginx = fullScriptPath + '/nginx/Dockerfile.' + framework
    elif framework == 'nodejs' or framework == 'reactjs':
        file_object.write('COPY nginx/' + appName + '.conf /etc/nginx/conf.d/default.conf\n')
        file_object.close()
        frontEndNginx = fullScriptPath + '/nginx/Dockerfile.' + framework
    else:
        print('Check for a valid framework name in your config file')
        frontEndNginx = "1"

    return frontEndNginx

def runBuild(
    framework, 
    version, 
    projectPath, 
    awsEcrRepository, 
    appName, 
    appNginxSidecar, 
    domainToUse, 
    cmdPath, 
    buildTag
):
    imageBuild = []
    imageCreated    = ""
    jsonOutput      = ""
    nginxImg        = ""
    nginxJsonOutput = ""
    
    printStep("Start Building Image Tag: " + awsEcrRepository + ':' + buildTag )
    fullScriptPath    = os.path.abspath(os.path.dirname(cmdPath))
    dockercli = docker.from_env()
    print('Provide Environment file \n')
    if os.path.isfile(fullScriptPath + '/env.files/' + "{}.template".format(framework)):
        src = fullScriptPath + '/env.files/' + "{}.template".format(framework)
        dst = fullScriptPath + '/' + projectPath + '/.env'
        copyfile(src, dst)

    if framework == 'laravel':
        if (os.path.isfile(fullScriptPath + '/' + framework + '/' + version + '/Dockerfile')):
            buildFilePath   = (framework + '/' + version + '/Dockerfile')
            dockerFile      = fullScriptPath + '/' + framework + '/' + version + '/Dockerfile'
        else:
            print('There was an error looking up for the Dockerfile')
            sys.exit(1)   
    else:
        dockerFile      = fullScriptPath + '/' + framework + '/Dockerfile'

    if ( os.path.isdir(fullScriptPath + '/' + projectPath) ) :
        buildProjectDirectory =  projectPath 

    else:
        print('There was a problen finding our project directory to dockerize')
        sys.exit(1)
    
    if framework == 'laravel':
        print("*** 1. Running Composer Install ***")    
        dockercli.containers.run('jakzal/phpqa:alpine', 'composer install --no-interaction --prefer-dist --optimize-autoloader', \
                                volumes={fullScriptPath + '/' + projectPath:{'bind': '/project', 'mode': 'rw'}}, \
                                working_dir='/project' )
    
        print("*** 2. Running php artisan key:generate ***")
        dockercli.containers.run('jakzal/phpqa:alpine', 'php artisan key:generate', \
                                volumes={fullScriptPath + '/' + projectPath:{'bind': '/project', 'mode': 'rw'}}, \
                                working_dir='/project')
    
    print("*** 3. Build Image Steps ***")
    print("    - Project Directory: " + fullScriptPath + '/' + projectPath)
    print("    - IMage Tag Created: " + awsEcrRepository + ':' + buildTag)
    print("    - Dockerfile Directory: " + dockerFile + '\n\n') 
    
    try:
        imageCreated, jsonOutput = dockercli.images.build( path=fullScriptPath + '/' + projectPath + '/', \
                                                            tag=awsEcrRepository + ':' + buildTag, \
                                                            dockerfile=dockerFile, \
                                                            forcerm=True)
        if appNginxSidecar == "yes" :
            print('*** 3.1 Building sidecar nginx image ***')
            nginxDockerFile  = createDockerFie(fullScriptPath, appName, domainToUse, projectPath, framework)

            if nginxDockerFile == "1":
                print("Error building NGINX Dockerfile\n\n")
                sys.exit(1)

            print("   Building NGINX image with the following parameters: \n" + \
                    "   - Build Path: " + fullScriptPath + "\n" + \
                    "   - Build Tag: "  +  awsEcrRepository + ':nginx-svc-' + buildTag + '\n' + \
                    "   - Build Dockerfile: " + fullScriptPath + '/nginx/Dockerfile' + '\n'
            )
             #fullScriptPath + '/nginx/Dockerfile',
            nginxImg, nginxJsonOutput = dockercli.images.build( path=fullScriptPath, \
                                                                tag=awsEcrRepository + ':nginx-svc-' + buildTag, \
                                                                dockerfile=nginxDockerFile,  
                                                                forcerm=True )
    

    except  docker.errors.BuildError as buildError:
            print('There was an error building this image: ' + str(buildError))
            sys.exit(1)
    except docker.errors.APIError as apiError:
            print("Error received from  server: " + str(apiError) ) 
            sys.exit(1)
    except KeyboardInterrupt as keyI:
            print("Keyboard Interruption Received")
            sys.exit(1)
    except FileNotFoundError as fNotFound:
            print("Could not process this request because the file %s was NOT FOUND", dockerFile)
            sys.exit(1)

    imageBuild.append(str(imageCreated).split("'")[1].strip("'").lstrip())
    
    if appNginxSidecar == "yes" :
        imageBuild.append(str(nginxImg).split("'")[1].strip("'").lstrip())
    
    printFinihedStep("Image Ready to Push ")

    return imageBuild


def pushImagetoEcr( localImage, awsEcrRepository ):
    
    printStep("Start Pushing Image : " + localImage )    
    ecrSession  = boto3.Session()
    ecrResponse = ecrSession.client('ecr').get_authorization_token()
    ecrToken    = ecrResponse['authorizationData'][0]['authorizationToken']
    ecrToken    = base64.b64decode(ecrToken).decode()
    ecrUser, ecrPasswd = ecrToken.split(':')
    authConfig  = {'username': ecrUser, 'password': ecrPasswd}
    
    dockerClient    = docker.from_env()
    ecrRegistry, projectRepo = awsEcrRepository.split('/')
    registry_url = ecrResponse['authorizationData'][0]['proxyEndpoint'].replace("https://", "")
    
    for output in dockerClient.images.push( localImage, \
                                            auth_config=authConfig, \
                                            stream=True, \
                                            decode=True):
        print (output)

    printFinihedStep("Finish Push Image to ECR Repo")
    dockerClient.images.remove(localImage, force=True)

def main() :
    if len(sys.argv) < 2: 
            print("Error while processing stack config file, no configuration file was found running this process")
            sys.exit(1)

    # Read json config file into variables
    appBaseDir, appDetails, dbsConfig, customInfo = getConfigInfo( sys.argv[1] )
    
    for app in appDetails:
        
        dockerImage = ""
        app['projectPath'] = str(check_output(['echo {}'.format(app['cloneInto'])], shell=True).strip(), 'utf-8')
        
        projectPath = appBaseDir + '/' + app['projectPath']
        gitCloneSrcCode(app['repoName'], projectPath)
        gitCommit = gitGetVersion(app['repoName'])
        
        dockerImage = runBuild( app['framework'], app['version'], projectPath, \
                                app['awsEcrRepository'], app['name'], app['nginxSidecar'], \
                                app['domainToUse'], sys.argv[0], gitCommit )

        if len(sys.argv) == 3 and sys.argv[2] == 'local':
            print ("We'll create only local imagws without pushing \n")
            continue

        for img in dockerImage:
            print('Processing ' + img + '\n')
            pushImagetoEcr(img, app['awsEcrRepository'])

if __name__ == "__main__":
    main()

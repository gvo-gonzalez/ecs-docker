FROM node:latest

ADD . '/usr/local'

WORKDIR '/usr/local/app'

RUN npm install

RUN npm install express --save

EXPOSE 3000

CMD [ "npm", "start" ]
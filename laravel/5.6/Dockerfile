FROM php:5.6-fpm

RUN rm /etc/apt/preferences.d/no-debian-php

RUN apt-get update

RUN apt-get install -y python php5-cli php5-mysql \
    php5-redis php5-readline libmcrypt-dev libcurl4-gnutls-dev zlib1g-dev \
    libicu-dev g++ libxml2-dev libpq-dev git zip unzip

RUN docker-php-ext-install mcrypt pdo pdo_mysql curl json xml pcntl soap

RUN pecl install mongo && \
    echo "extension=mongo.so" > /usr/local/etc/php/conf.d/ext-mongo.ini

RUN curl -sS https://getcomposer.org/installer | php
RUN mv composer.phar /usr/bin/composer

RUN apt-get autoremove && apt-get autoclean \
 && rm -rf /var/lib/apt/lists/*
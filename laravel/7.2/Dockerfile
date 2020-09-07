FROM php:7.2-fpm
# Copy composer.lock and composer.json
ADD composer.lock /var/www 
ADD composer.json /var/www

# Set working directory
WORKDIR /var/www

# Install Dependencies 
RUN apt-get update && apt-get install -y \
    git libmcrypt-dev libcurl4-gnutls-dev \
    zlib1g-dev libicu-dev g++ libxml2-dev \
    libpq-dev zip unzip \
    build-essential default-mysql-client \
    libpng-dev libjpeg62-turbo-dev \
    libfreetype6-dev locales \
    jpegoptim optipng pngquant gifsicle \
    vim curl

# Install PHP Extensions
RUN git clone https://github.com/phpredis/phpredis.git /usr/src/php/ext/redis \
 && docker-php-ext-install pdo pdo_mysql curl json xml redis exif pcntl mbstring zip
RUN docker-php-ext-configure gd --with-gd --with-freetype-dir=/usr/include/ --with-jpeg-dir=/usr/include/ --with-png-dir=/usr/include/
RUN docker-php-ext-install gd

# Install composer
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

RUN apt-get autoremove -y && apt-get autoclean \
 && rm -rf /var/lib/apt/lists/*

# Add user for laravel application
RUN groupadd -g 1000 www
RUN useradd -u 1000 -ms /bin/bash -g www www 

# Append our application 
COPY --chown=www:www . /var/www

# Update user 
USER www
ENTRYPOINT [ "/bin/bash", "-c", "(php artisan migrate || true) && \
                          (php artisan migrate:refresh --seed || true) && \
                          (php artisan key:generate || true) && \
                          (php artisan config:cache || true) && \
                          (php artisan route:cache || true) && \
                          (php-fpm || true)" ]

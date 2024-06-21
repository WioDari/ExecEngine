#Debian is preferred, depends on api module
FROM buildpack-deps:latest

#GNU-GCC compiler
#installed versions: 13.3.0
#choose preferred version on mirror site
#https://ftpmirror.gnu.org/gnu/gcc/
ENV GCC_VERSIONS \
  13.3.0
RUN set -xe && \
  for VERSION in $GCC_VERSIONS; do \
    curl -fSsl -k "https://ftp.gnu.org/gnu/gcc/gcc-$VERSION/gcc-$VERSION.tar.gz" -o /tmp/gcc-$VERSION.tar.gz && \
    mkdir /tmp/gcc-$VERSION && \
    tar -xf /tmp/gcc-$VERSION.tar.gz -C /tmp/gcc-$VERSION --strip-components=1 && \
    rm /tmp/gcc-$VERSION.tar.gz && \
    cd /tmp/gcc-$VERSION && \
    ./contrib/download_prerequisites && \
    { rm *.tar.* || true; } && \
    tmpdir="$(mktemp -d)" && \
    cd "$tmpdir" && \
    /tmp/gcc-$VERSION/configure \
      --disable-multilib \
      --enable-languages=c,c++ \
      --prefix=/usr/local/gcc-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install-strip && \
    rm -rf /tmp/*; \
  done

#Python compilers
#installed versions: 2.7.17, 3.12.4
#choose preferred version on mirror site
#https://www.python.org/ftp/python/
ENV PYTHON_VERSIONS \
  2.7.17 \
  3.12.4
RUN set -xe && \
  for VERSION in $PYTHON_VERSIONS; do \
    curl -fSsl "https://www.python.org/ftp/python/$VERSION/Python-$VERSION.tar.xz" -o /tmp/python-$VERSION.tar.xz && \
    mkdir /tmp/python-$VERSION && \
    tar -xf /tmp/python-$VERSION.tar.xz -C /tmp/python-$VERSION --strip-components=1 && \
    rm /tmp/python-$VERSION.tar.xz && \
    cd /tmp/python-$VERSION && \
    ./configure \
      --prefix=/usr/local/python-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#Assembler compilers
#installed versions: 2.16.03
#check for newer version on mirror site
#https://www.nasm.us/pub/releasebuilds/
ENV NASM_VERSIONS \
  2.16.03
RUN set -xe && \
  for VERSION in $NASM_VERSIONS; do \
    curl -fSsl -k "https://www.nasm.us/pub/nasm/releasebuilds/$VERSION/nasm-$VERSION.tar.gz" -o /tmp/nasm-$VERSION.tar.gz && \
    mkdir /tmp/nasm-$VERSION && \
    tar -xf /tmp/nasm-$VERSION.tar.gz -C /tmp/nasm-$VERSION --strip-components=1 && \
    rm /tmp/nasm-$VERSION.tar.gz && \
    cd /tmp/nasm-$VERSION && \
    ./configure \
      --prefix=/usr/local/nasm-$VERSION && \
    make -j$(nproc) nasm ndisasm && \
    make -j$(nproc) strip && \
    make -j$(nproc) install && \
    echo "/usr/local/nasm-$VERSION/bin/nasm -o main.o \$@ && ld main.o" >> /usr/local/nasm-$VERSION/bin/nasmld && \
    chmod +x /usr/local/nasm-$VERSION/bin/nasmld && \
    rm -rf /tmp/*; \
  done

#PHP compilers
#installed versions: 8.3.8
#select preferred version on PHP official site:
#https://www.php.net/distributions/
ENV PHP_VERSIONS \
  8.3.8
RUN set -xe && \
  apt-get update && \
  apt-get install -y bison re2c && \
  rm -rf /var/lib/apt/lists/* && \
  for VERSION in $PHP_VERSIONS; do \
    curl -fSsl "https://www.php.net/distributions/php-$VERSION.tar.gz" -o /tmp/php-$VERSION.tar.gz && \
    mkdir /tmp/php-$VERSION && \
    tar -xf /tmp/php-$VERSION.tar.gz -C /tmp/php-$VERSION --strip-components=1 && \
    rm /tmp/php-$VERSION.tar.gz && \
    cd /tmp/php-$VERSION && \
    ./buildconf -f && \
    ./configure \
      --prefix=/usr/local/php-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#Bash
#installed version: 5.2.21
#select preferred version on mirror site:
#https://ftp.gnu.org/gnu/bash/
ENV BASH_VERSIONS \
  5.2.21
RUN set -xe && \
  for VERSION in $BASH_VERSIONS; do \
    curl -fSsl "https://ftp.gnu.org/gnu/bash/bash-$VERSION.tar.gz" -o /tmp/bash-$VERSION.tar.gz && \
    mkdir /tmp/bash-$VERSION && \
    tar -xf /tmp/bash-$VERSION.tar.gz -C /tmp/bash-$VERSION --strip-components=1 && \
    rm /tmp/bash-$VERSION.tar.gz && \
    cd /tmp/bash-$VERSION && \
    ./configure \
      --prefix=/usr/local/bash-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install & \
    rm -rf /tmp/*; \
  done

#Pascal compilers

#display info about compilers
#mostly used for debug
#would be removed in future versions
#(also shows commands for run scripts on diff langs)
CMD /usr/local/gcc-13.3.0/g++ --version
CMD /usr/local/python-2.7.17/python2 -v
CMD /usr/local/python-3.12.4/python3 -v
CMD /usr/local/nasm-2.16.03/bin/nasmld -v
CMD /usr/local/php-8.3.8/bin/php -v
CMD /usr/local/bash-5.2.21/bin/bash -v

LABEL maintaner="Danila Fateenkov, wiosnagd97@gmail.com"
LABEL version="0.1.0"

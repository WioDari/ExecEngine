#Debian is preferred, depends on API module
FROM buildpack-deps:latest

#GNU-GCC
#installed versions: 12.4.0
#choose preferred version on mirror site
#https://ftpmirror.gnu.org/gnu/gcc/
ENV GCC_VERSIONS \
  12.4.0
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

#Python
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

#PyPy compilers
#PyPy version: 7.3.16
#check for latest versions on official page:
#https://www.pypy.org/
#Python versions: 2.7 and 3.10
ENV PYPY_VERSION 7.3.16
ENV PYTHON_VERSIONS \
  3.10 \
  2.7
RUN set -xe && \
  for VERSION in $PYTHON_VERSIONS; do \
    curl -fSsl "https://downloads.python.org/pypy/pypy$VERSION-v$PYPY_VERSION-linux64.tar.bz2" -o /tmp/pypy$VERSION.tar.bz2 && \
    mkdir /usr/local/pypy$VERSION && \
    tar -xf /tmp/pypy$VERSION.tar.bz2 -C /usr/local/pypy$VERSION --strip-components=1 && \
    ln -s /usr/local/pypy$VERSION/bin/pypy /usr/bin/pypy$VERSION && \
    rm -rf /tmp/*; \
  done

#Assembly
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

#PHP
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
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#Java
#you can add more version
#but be careful with download links (add more statements in if ... else)
#if needed.
#select other versions here:
#https://jdk.java.net/
ENV JAVA_VERSIONS \
  22
RUN set -xe && \
  for VERSION in $JAVA_VERSIONS; do \
    if [ $VERSION = 17 || $VERSION = 21 ]; then \
      URL="https://download.java.net/openjdk/jdk$VERSION/ri/openjdk-$VERSION+35_linux-x64_bin.tar.gz"; \
    else \
      URL="https://download.java.net/openjdk/jdk$VERSION/ri/openjdk-$VERSION+36_linux-x64_bin.tar.gz"; \
    fi; \
    curl -fSsl -k "$URL" -o /tmp/openjdk-$VERSION.tar.gz && \
    mkdir /usr/local/openjdk$VERSION && \
    tar -xf /tmp/openjdk-$VERSION.tar.gz -C /usr/local/openjdk$VERSION --strip-components=1 && \
    ln -s /usr/local/openjdk$VERSION/bin/java /usr/bin/java && \
    ln -s /usr/local/openjdk$VERSION/bin/jar /usr/bin/jar && \
    ln -s /usr/local/openjdk$VERSION/bin/javac /usr/bin/javac && \
    rm -rf /tmp/*; \
  done

#Ruby compilers
#you can choose preferred versions here:
#https://cache.ruby-lang.org/pub/ruby/
ENV RUBY_VERSIONS \
  3.3.3
RUN set -xe && \
  for VERSION in $RUBY_VERSIONS; do \
    curl -fSsl "https://cache.ruby-lang.org/pub/ruby/${VERSION%.*}/ruby-$VERSION.tar.gz" -o /tmp/ruby-$VERSION.tar.gz && \
    mkdir /tmp/ruby-$VERSION && \
    tar -xf /tmp/ruby-$VERSION.tar.gz -C /tmp/ruby-$VERSION --strip-components=1 && \
    cd /tmp/ruby-$VERSION && \
    ./configure \
      --prefix=/usr/local/ruby-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#NodeJS compilers
#you can choose preferred versions here:
#https://www.nodejs.org/dist
ENV NODE_VERSIONS \
  20.15.0
RUN set -xe && \
  for VERSION in $NODE_VERSIONS; do \
    curl -fSsl "https://nodejs.org/dist/v$VERSION/node-v$VERSION.tar.gz" -o /tmp/node-$VERSION.tar.gz && \
    mkdir /tmp/node-$VERSION && \
    tar -xf /tmp/node-$VERSION.tar.gz -C /tmp/node-$VERSION --strip-components=1 && \
    cd /tmp/node-$VERSION && \
    ./configure \
      --prefix=/usr/local/node-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#FreePascal
#installed version: 3.2.2
#check for newer version on official site:
#https://downloads.freepascal.org/fpc/dist/
ENV PASCAL_VERSIONS \
  3.2.2
RUN set -xe && \
  for VERSION in $PASCAL_VERSIONS; do \
    curl -fSsl "https://downloads.freepascal.org/fpc/dist/$VERSION/x86_64-linux/fpc-$VERSION.x86_64-linux.tar" -o /tmp/fpc-$VERSION.tar && \
    mkdir /tmp/fpc-$VERSION && \
    tar -xf /tmp/fpc-$VERSION.tar -C /tmp/fpc-$VERSION --strip-components=1 && \
    rm /tmp/fpc-$VERSION.tar && \
    cd /tmp/fpc-$VERSION && \
    echo "/usr/local/fpc-$VERSION" | ./install.sh  && \
    ln -s /usr/local/fpc-$VERSION/bin/fpc /usr/bin/fpc && \
    ln -s /usr/local/fpc-$VERSION/bin/ppcx64 /usr/bin/ppcx64 && \
    rm -rf /tmp/*; \
  done

#Dart
#installed versions: 3.4.4
#check for new versions here:
#https://dart.dev/get-dart/archive
ENV DART_VERSIONS \
  3.4.4
RUN set -xe && \
  apt-get update && \
  apt-get install -y unzip && \
  rm -rf /var/lib/apt/lists/* && \
  for VERSION in $DART_VERSIONS; do \
    curl -fSsl "https://storage.googleapis.com/dart-archive/channels/stable/release/$VERSION/sdk/dartsdk-linux-x64-release.zip" -o /tmp/dart-$VERSION.zip && \
    unzip -d /usr/local/dart-$VERSION /tmp/dart-$VERSION.zip && \
    ln -s /usr/local/dart-$VERSION/dart-sdk/bin/dart /usr/bin/dart && \
    rm -rf /tmp/*; \
  done

#Go
#installed versions: 1.22.4
#latest versions:
#https://go.dev/doc/install
ENV GO_VERSIONS \
  1.22.4
RUN set -xe && \
  for VERSION in $GO_VERSIONS; do \
    curl -fSsl "https://dl.google.com/go/go$VERSION.linux-amd64.tar.gz" -o /tmp/golang-$VERSION.tar.gz && \
    mkdir /usr/local/go-$VERSION && \
    tar -xf /tmp/golang-$VERSION.tar.gz -C /usr/local/go-$VERSION --strip-components=1 && \
    ln -s /usr/local/golang-$VERSION/bin/go /usr/bin/go && \
    rm -rf /tmp/*; \
  done

#Rust
#installed versions: 1.79.0
#check latest version here:
#https://forge.rust-lang.org/infra/other-installation-methods.html#source-code
ENV RUST_VERSIONS \
  1.79.0
RUN set -xe && \
  for VERSION in $RUST_VERSIONS; do \
    curl -fSsl "https://static.rust-lang.org/dist/rust-$VERSION-x86_64-unknown-linux-gnu.tar.gz" -o /tmp/rust-$VERSION.tar.gz && \
    mkdir /tmp/rust-$VERSION && \
    tar -xf /tmp/rust-$VERSION.tar.gz -C /tmp/rust-$VERSION --strip-components=1 && \
    cd /tmp/rust-$VERSION && \
    ./install.sh \
      --prefix=/usr/local/rust-$VERSION \
      --components=rustc,rust-std-x86_64-unknown-linux-gnu && \
    rm -rf /tmp/*; \
  done

#Kotlin
#installed version: 2.0.0
#check latest version here:
#https://github.com/JetBrains/kotlin/releases/
ENV KOTLIN_VERSIONS \
  2.0.0
RUN set -xe && \
  apt-get update && \
  apt-get install -y unzip && \
  rm -rf /var/lib/apt/lists/* && \
  for VERSION in $KOTLIN_VERSIONS; do \
    curl -fSsL "https://github.com/JetBrains/kotlin/releases/download/v$VERSION/kotlin-compiler-$VERSION.zip" -o /tmp/kotlin-compiler-$VERSION.zip && \
    mkdir /usr/local/kotlin-$VERSION && \
    unzip /tmp/kotlin-compiler-$VERSION.zip -d /usr/local/kotlin-$VERSION && \
    rm -rf /tmp/*; \
  done

#Swift
#installed versions: 5.10.1
#check latest version here:
#https://github.com/swiftlang/swift/releases/
ENV SWIFT_VERSIONS \
  5.10.1
RUN set -xe && \
  for VERSION in $SWIFT_VERSIONS; do \
    curl -fSsL "https://download.swift.org/swift-$VERSION-release/debian12/swift-$VERSION-RELEASE/swift-$VERSION-RELEASE-debian12.tar.gz" -o /tmp/swift-$VERSION.tar.gz && \
    mkdir /usr/local/swift-$VERSION && \
    tar -xf /tmp/swift-$VERSION.tar.gz -C /usr/local/swift-$VERSION --strip-components=2 && \
    rm -rf /tmp/*; \
  done
 
RUN set -xe && \
    apt-get update && \
    apt-get install -y --no-install-recommends git libcap-dev libsystemd-dev && \
    rm -rf /var/lib/apt/lists/* && \
    git clone https://github.com/ioi/isolate.git /tmp/isolate && \
    cd /tmp/isolate && \
    git checkout 758ab000e3a1bcf1e57ffddea2340ffa1a5af49b && \
    make -j$(nproc) install && \
    rm -rf /tmp/*

COPY tests /usr/local/tests

RUN mkdir -p /opt/compilers

RUN cp /usr/local/nasm-2.16.03/bin/nasm /opt/compilers/
RUN cp /usr/local/bash-5.2.21/bin/bash /opt/compilers/
RUN cp /usr/local/gcc-12.4.0/bin/g++ /opt/compilers/
RUN cp /usr/local/gcc-12.4.0/bin/gcc /opt/compilers/
RUN cp /usr/local/dart-3.4.4/dart-sdk/bin/dart /opt/compilers/
RUN cp /usr/local/go-1.22.4/bin/go /opt/compilers/
RUN cp /usr/local/php-8.3.8/bin/php /opt/compilers/
RUN cp /usr/local/openjdk22/bin/java /opt/compilers/
RUN cp /usr/local/openjdk22/bin/javac /opt/compilers/
RUN cp /usr/local/node-20.15.0/bin/node /opt/compilers/
RUN cp /usr/local/kotlin-2.0.0/kotlinc/bin/kotlin /opt/compilers/
RUN cp /usr/local/kotlin-2.0.0/kotlinc/bin/kotlinc /opt/compilers/
RUN cp /usr/local/fpc-3.2.2/bin/fpc /opt/compilers/
RUN cp /usr/local/python-2.7.17/bin/python2 /opt/compilers/
RUN cp /usr/local/python-3.12.4/bin/python3 /opt/compilers/
RUN cp /usr/local/pypy3.10/bin/pypy /opt/compilers/pypy3
RUN cp /usr/local/pypy2.7/bin/pypy /opt/compilers/pypy2
RUN cp /usr/local/ruby-3.3.3/bin/ruby /opt/compilers/
RUN cp /usr/local/rust-1.79.0/bin/rustc /opt/compilers/
RUN cp /usr/local/swift-5.10.1/bin/swift /opt/compilers/
#RUN cp /usr/local/d-2.109.1/linux64/bin/dmd /opt/compilers/
#RUN cp /usr/local/scala-3.3.3/bin/scalac /opt/compilers/
#RUN cp /usr/local/scala-3.3.3/bin/scala /opt/compilers/

RUN chmod +x /opt/compilers/*

LABEL maintaner="Danila Fateenkov, wiosnagd97@gmail.com"
LABEL version="0.1.4"
FROM buildpack-deps:bookworm

#GNU-GCC
#https://ftpmirror.gnu.org/gnu/gcc/
ENV GCC_VERSIONS \
  12.4.0
RUN set -xe && \
  for VERSION in $GCC_VERSIONS; do \
    curl -fSsl -k "https://mirrorservice.org/sites/sourceware.org/pub/gcc/releases/gcc-$VERSION/gcc-$VERSION.tar.gz" -o /tmp/gcc-$VERSION.tar.gz && \
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
      --enable-languages=c,c++,objc,fortran \
      --prefix=/usr/local/gcc-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install-strip && \
    rm -rf /tmp/*; \
  done

#Python
#https://www.python.org/ftp/python/
ENV PYTHON_VERSIONS \
  2.7.17 \
  3.13.5
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

#PyPy
#PyPy version: 7.3.20
#https://www.pypy.org/
#Python versions: 2.7 and 3.11
ENV PYPY_VERSION 7.3.20
ENV PYTHON_VERSIONS \
  3.11 \
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
#https://ftp.gnu.org/gnu/bash/
ENV BASH_VERSIONS \
  5.2.21
RUN set -xe && \
  for VERSION in $BASH_VERSIONS; do \
    curl -fSsl "https://www.mirrorservice.org/sites/ftp.gnu.org/gnu/bash/bash-$VERSION.tar.gz" -o /tmp/bash-$VERSION.tar.gz && \
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

#Ruby
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

#NodeJS
#https://www.nodejs.org/dist
ENV NODE_VERSIONS \
  21.7.3
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
#https://downloads.freepascal.org/fpc/dist/
ENV PASCAL_VERSIONS \
  3.2.2
RUN set -xe && \
  for VERSION in $PASCAL_VERSIONS; do \
    curl -fSsL "https://sourceforge.net/projects/freepascal/files/Linux/$VERSION/fpc-$VERSION.x86_64-linux.tar/download" -o /tmp/fpc-$VERSION.tar && \
    mkdir /tmp/fpc-$VERSION && \
    tar -xf /tmp/fpc-$VERSION.tar -C /tmp/fpc-$VERSION --strip-components=1 && \
    rm /tmp/fpc-$VERSION.tar && \
    cd /tmp/fpc-$VERSION && \
    echo "/usr/local/fpc-$VERSION" | ./install.sh && \
    rm -rf /tmp/*; \
  done

#Dart
#https://dart.dev/get-dart/archive
ENV DART_VERSIONS \
  3.8.2
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
#https://go.dev/doc/install
ENV GO_VERSIONS \
  1.24.5
RUN set -xe && \
  for VERSION in $GO_VERSIONS; do \
    curl -fSsl "https://dl.google.com/go/go$VERSION.linux-amd64.tar.gz" -o /tmp/golang-$VERSION.tar.gz && \
    mkdir /usr/local/go-$VERSION && \
    tar -xf /tmp/golang-$VERSION.tar.gz -C /usr/local/go-$VERSION --strip-components=1 && \
    ln -s /usr/local/golang-$VERSION/bin/go /usr/bin/go && \
    rm -rf /tmp/*; \
  done

#Rust
#https://forge.rust-lang.org/infra/other-installation-methods.html#source-code
ENV RUST_VERSIONS \
  1.88.0
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
#https://github.com/JetBrains/kotlin/releases/
ENV KOTLIN_VERSIONS \
  2.2.0
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

#.NET SDK (F#, Visual Basic, C#)
#https://dotnet.microsoft.com/en-us/download
ENV DOTNET_VERSIONS \
  8.0.412
RUN set -xe && \
  for VERSION in $DOTNET_VERSIONS; do \
    curl -fSsL "https://builds.dotnet.microsoft.com/dotnet/Sdk/$VERSION/dotnet-sdk-$VERSION-linux-x64.tar.gz" -o /tmp/dotnet-$VERSION.tar.gz && \
    mkdir /usr/local/dotnet-$VERSION && \
    tar -xf /tmp/dotnet-$VERSION.tar.gz -C /usr/local/dotnet-$VERSION && \
    rm -rf /tmp/*; \
  done

#R
#https://cloud.r-project.org/src/base/R-4
ENV R_VERSIONS \
  4.5.1
RUN set -xe && \
  apt-get update && \
  apt-get install -y --no-install-recommends r-base-dev libpcre2-dev && \
  rm -rf /var/lib/apt/lists/* && \
  for VERSION in $R_VERSIONS; do \
    curl -fSsL "https://cloud.r-project.org/src/base/R-4/R-$VERSION.tar.gz" -o /tmp/r-$VERSION.tar.gz && \
    mkdir /tmp/r-$VERSION && \
    tar -xf /tmp/r-$VERSION.tar.gz -C /tmp/r-$VERSION --strip-components=1 && \
    rm /tmp/r-$VERSION.tar.gz && \
    cd /tmp/r-$VERSION && \
    ./configure \
      --prefix=/usr/local/r-$VERSION \
      --enable-R-shlib && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#Scala
#https://github.com/scala/scala3
ENV SCALA_VERSIONS \
  3.7.1
RUN set -xe && \
  for VERSION in $SCALA_VERSIONS; do \
    curl -fSsL "https://github.com/scala/scala3/releases/download/$VERSION/scala3-$VERSION-x86_64-pc-linux.tar.gz" -o /tmp/scala-$VERSION.tar.gz && \
    mkdir /usr/local/scala-$VERSION && \
    tar -xf /tmp/scala-$VERSION.tar.gz -C /usr/local/scala-$VERSION --strip-components=1 && \
    rm -rf /tmp/*; \
  done

#D
#http://downloads.dlang.org/releases/2.x/
ENV D_VERSIONS \
  2.111.0
RUN set -xe && \
  for VERSION in $D_VERSIONS; do \
    curl -fSsL "http://downloads.dlang.org/releases/2.x/$VERSION/dmd.$VERSION.linux.tar.xz" -o /tmp/d-$VERSION.tar.gz && \
    mkdir /usr/local/d-$VERSION && \
    tar -xf /tmp/d-$VERSION.tar.gz -C /usr/local/d-$VERSION --strip-components=1 && \
    rm -rf /usr/local/d-$VERSION/linux/*32 && \
    rm -rf /tmp/*; \
  done

#FreeBASIC
#https://sourceforge.net/projects/fbc/files/
ENV FBC_VERSIONS \
  1.10.1
RUN set -xe && \
  apt-get update && \
  apt-get install -y --no-install-recommends libncurses5-dev libtinfo5 libgpm-dev libx11-dev libxext-dev libxpm-dev libxrandr-dev libxrender-dev libgl1-mesa-dev libffi-dev && \
  rm -rf /var/lib/apt/lists/* && \
  for VERSION in $FBC_VERSIONS; do \
    curl -fSsL "https://sourceforge.net/projects/fbc/files/FreeBASIC-$VERSION/Binaries-Linux/FreeBASIC-$VERSION-linux-x86_64.tar.gz/download" -o /tmp/fbc-$VERSION.tar.gz && \
    mkdir /usr/local/fbc-$VERSION && \
    tar -xf /tmp/fbc-$VERSION.tar.gz -C /usr/local/fbc-$VERSION --strip-components=1 && \
    rm -rf /tmp/*; \
  done

#Lua
#https://www.lua.org/ftp/
ENV LUA_VERSIONS \
  5.4.8
RUN set -xe && \
  for VERSION in $LUA_VERSIONS; do \
    curl -fSsL "https://www.lua.org/ftp/lua-$VERSION.tar.gz" -o /tmp/lua-$VERSION.tar.gz && \
    mkdir /usr/local/lua-$VERSION && \
    tar -xf /tmp/lua-$VERSION.tar.gz -C /usr/local/lua-$VERSION --strip-components=1 && \
    rm /tmp/lua-$VERSION.tar.gz && \
    cd /usr/local/lua-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#Haskell (GHC)
#https://downloads.haskell.org/~ghc/
ENV HASKELL_VERSIONS \
  9.12.2
RUN set -xe && \
  apt-get update && \
  apt-get install -y --no-install-recommends libgmp-dev libtinfo5 && \
  rm -rf /var/lib/apt/lists/* && \
  for VERSION in $HASKELL_VERSIONS; do \
    curl -fSsL "https://downloads.haskell.org/~ghc/$VERSION/ghc-$VERSION-x86_64-deb10-linux.tar.gz" -o /tmp/haskell-$VERSION.tar.gz && \
    mkdir /tmp/haskell-$VERSION && \
    tar -xf /tmp/haskell-$VERSION.tar.gz -C /tmp/haskell-$VERSION --strip-components=1 && \
    rm /tmp/haskell-$VERSION.tar.gz && \
    cd /tmp/haskell-$VERSION && \
    ./configure \
      --prefix=/usr/local/haskell-$VERSION && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#SQLite
#https://www.sqlite.org/
ENV SQLITE_VERSION \
  3.50.4
ENV SQLITE_VERSION_DOWNLOAD \
  3500400
RUN set -xe && \
  for VERSION in $SQLITE_VERSION; do \
    curl -fSsL "https://www.sqlite.org/2025/sqlite-autoconf-$SQLITE_VERSION_DOWNLOAD.tar.gz" -o /tmp/sqlite-$SQLITE_VERSION.tar.gz && \
    mkdir /tmp/sqlite-$SQLITE_VERSION && \
    tar -xf /tmp/sqlite-$SQLITE_VERSION.tar.gz -C /tmp/sqlite-$SQLITE_VERSION --strip-components=1 && \
    rm /tmp/sqlite-$SQLITE_VERSION.tar.gz && \
    cd /tmp/sqlite-$SQLITE_VERSION && \
    ./configure \
      --prefix=/usr/local/sqlite-$SQLITE_VERSION \
      --enable-all && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#Prolog (GNU)
#http://www.gprolog.org/
ENV PROLOG_VERSIONS \
  1.5.0
RUN set -xe && \
  for VERSION in $PROLOG_VERSIONS; do \
    curl -fSsL "http://www.gprolog.org/gprolog-$VERSION.tar.gz" -o /tmp/prolog-$VERSION.tar.gz && \
    mkdir /tmp/prolog-$VERSION && \
    tar -xf /tmp/prolog-$VERSION.tar.gz -C /tmp/prolog-$VERSION --strip-components=1 && \
    rm /tmp/prolog-$VERSION.tar.gz && \
    cd /tmp/prolog-$VERSION/src && \
    ./configure \
      --prefix=/usr/local/prolog-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#OCaml
#https://github.com/ocaml/ocaml/releases
ENV OCAML_VERSIONS \
  5.3.0
RUN set -xe && \
  for VERSION in $OCAML_VERSIONS; do \
    curl -fSsL "https://github.com/ocaml/ocaml/archive/refs/tags/$VERSION.tar.gz" -o /tmp/ocaml-$VERSION.tar.gz && \
    mkdir /tmp/ocaml-$VERSION && \
    tar -xf /tmp/ocaml-$VERSION.tar.gz -C /tmp/ocaml-$VERSION --strip-components=1 && \
    rm /tmp/ocaml-$VERSION.tar.gz && \
    cd /tmp/ocaml-$VERSION && \
    ./configure \
      --prefix=/usr/local/ocaml-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#Octave (GNU)
#https://octave.org
ENV OCTAVE_VERSIONS \
  10.2.0
RUN set -xe && \
  apt-get update && \
  apt-get install -y --no-install-recommends gfortran libblas-dev liblapack-dev libpcre3-dev && \
  rm -rf /var/lib/apt/lists/* && \
  for VERSION in $OCTAVE_VERSIONS; do \
    curl -fSsL "https://mirror.us-midwest-1.nexcess.net/gnu/octave/octave-$VERSION.tar.gz" -o /tmp/octave-$VERSION.tar.gz && \
    mkdir /tmp/octave-$VERSION && \
    tar -xf /tmp/octave-$VERSION.tar.gz -C /tmp/octave-$VERSION --strip-components=1 && \
    rm /tmp/octave-$VERSION.tar.gz && \
    cd /tmp/octave-$VERSION && \
    ./configure \
      --prefix=/usr/local/octave-$VERSION && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /tmp/*; \
  done

#TypeScript
#https://github.com/microsoft/TypeScript/releases
ENV TYPESCRIPT_VERSIONS \
  5.9.2
RUN set -xe && \
  curl -fSsL "https://deb.nodesource.com/setup_12.x" | bash - && \
  apt-get update && \
  apt-get install -y --no-install-recommends nodejs npm && \
  rm -rf /var/lib/apt/lists/* && \
  for VERSION in $TYPESCRIPT_VERSIONS; do \
    npm install -g typescript@$VERSION; \
    rm -rf /tmp/*; \
  done

COPY tests /usr/local/tests

LABEL maintaner="Danila Fateenkov, wiosnagd97@gmail.com"
LABEL version="1.0.0"
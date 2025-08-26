# ExecEngine
ExecEngine is designed to run untrusted code in web-centric environments and applications. ExecEngine is divided into 2 main modules: API, on the basis of which you can create your own site for code testing and programming contests; and compilers module, which contains tests and Dockerfile for working with compilers.

Current version of docker image (compilers): 1.0.0

Current size of docker image (compilers): 13.5 GB

## Installation
1. Download and extract the release archive.
2. Open the execengine.ini file and change the DATABASE_USER, DATABASE_PASSWORD, RABBITMQ_USER, RABBITMQ_PASSWORD, ADMIN_USERNAME, ADMIN_PASSWORD, and SECRET_KEY parameters to unique values.
3. Open the docker-compose.ini file and change the POSTGRES_USER parameter (must match DATABASE_USER), POSTGRES_PASSWORD (must match DATABASE_PASSWORD), RABBITMQ_DEFAULT_USER (must match RABBITMQ_USER), RABBITMQ_DEFAULT_PASS (must match RABBITMQ_PASSWORD).
4. Start the service with the command `docker compose up --build`.

## Available languages

| Name                             | Version   |
|----------------------------------|-----------|
| Assembly (NASM)                  | 2.16.03   |
| Bash                             | 5.2.21    |
| Basic (FBC)                      | 1.10.1    |
| C (GNU GCC)                      | 12.4.0    |
| C# (.NET SDK)                    | 8.0.412   |
| C++ (GNU GCC)                    | 12.4.0    |
| D (DMD)                          | 2.111.0   |
| Dart                             | 3.4.4     |
| Fortran (GNU GCC)                | 12.4.0    |
| F# (.NET SDK)                    | 8.0.412   |
| Go                               | 1.22.4    |
| Haskell (GHC)                    | 9.12.2    |
| Java (OpenJDK)                   | 22        |
| JavaScript (NodeJS)              | 21.7.3    |
| Kotlin                           | 2.0.0     |
| Lua                              | 5.4.8     |
| Objective-C (GNU GCC)            | 12.4.0    |
| OCaml                            | 5.3.0     |
| Octave (GNU)                     | 10.2.0    |
| PHP                              | 8.3.8     |
| Pascal (FPC)                     | 3.2.2     |
| Perl                             | 5.36.0    |
| Prolog (GNU)                     | 1.5.0     |
| PyPy 2.7                         | 7.3.20    |
| PyPy 3.11                        | 7.3.20    |
| Python 2                         | 2.7.17    |
| Python 3                         | 3.13.5    |
| R                                | 4.5.1     |
| Ruby                             | 3.3.3     |
| Rust                             | 1.79.0    |
| Scala                            | 3.7.1     |
| SQLite                           | 5.30.4    |
| Swift                            | 5.10.1    |
| Text                             |           |
| Typescript                       | 5.9.2     |
| Visual Basic (.NET SDK)          | 8.0.412   |

Main inspiration: https://github.com/judge0/judge0/tree/master

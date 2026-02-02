# ExecEngine Compilers Image
This directory contains source code for building your own image of compilers for working with selected programming languages in ExecEngine. 
Current version: 1.1.0

## Changing the list of programming languages
You can change the list of available programming languages at your discretion. We strongly recommend performing this procedure before running ExecEngine for the first time. To do this:
1. Go to the /tests directory. This directory contains test data sets and configuration files for all pre-installed programming languages. 
2. To remove a programming language that you do not plan to use, go to the directory for that language and create an empty file named `.skip`.
3. Exit the /tests directory and run the `parse_properties.py` script to generate a JSON file describing the selected programming languages.
4. A JSON file named `languages.json` will be created in the root directory of the compiler image. Move this file to the execengine/app/db directory.
5. Launch the API service with the appropriate command and check the list of available programming languages.
Please note that this method does not involve removing unused programming languages, which means that the full list of languages will still be available in the API.

## Editing the image of compilers
You can manually edit the Dockerfile of the compiler image and build it locally if necessary. All processes for installing and compiling programming languages are documented, so you can easily find the programming language you need and remove it (or change its version in the corresponding variable).
To build the image of the compilers, use the command (first navigate to the /compilers directory so that Docker can find the corresponding Dockerfile):
`docker build -t <your_image_name> .`

## Available languages

| Name                             | Version   |
|----------------------------------|-----------|
| Assembly (NASM)                  | 2.16.03   |
| Bash                             | 5.2.21    |
| Basic (FBC)                      | 1.10.1    |
| C (CLang)                        | 21.1.2    |
| C (GNU GCC)                      | 14.3.0    |
| C# (.NET SDK)                    | 8.0.412   |
| C++ (CLang)                      | 21.1.2    |
| C++ (GNU GCC)                    | 14.3.0    |
| D (DMD)                          | 2.111.0   |
| Dart                             | 3.8.2     |
| Executable                       |           |
| Fortran (GNU GCC)                | 14.3.0    |
| F# (.NET SDK)                    | 8.0.412   |
| Go                               | 1.24.5    |
| Haskell (GHC)                    | 9.12.2    |
| Java (OpenJDK)                   | 22        |
| JavaScript (NodeJS)              | 21.7.3    |
| Kotlin                           | 2.2.0     |
| Lua                              | 5.4.8     |
| Objective-C (GNU GCC)            | 14.3.0    |
| OCaml                            | 5.3.0     |
| Octave (GNU)                     | 10.2.0    |
| PHP                              | 8.4.10    |
| Pascal (FPC)                     | 3.2.2     |
| Perl                             | 5.36.0    |
| Prolog (GNU)                     | 1.5.0     |
| PyPy 2.7                         | 7.3.20    |
| PyPy 3.11                        | 7.3.20    |
| Python 2                         | 2.7.17    |
| Python 3                         | 3.13.5    |
| R                                | 4.5.1     |
| Ruby                             | 3.4.5     |
| Rust                             | 1.88.0    |
| Scala                            | 3.7.1     |
| SQLite                           | 5.30.4    |
| Swift                            | 6.1.2     |
| Text                             |           |
| Typescript                       | 5.9.2     |
| Visual Basic (.NET SDK)          | 8.0.412   |

## Credits
The image of compilers for the Judge0 system was taken as a basis: https://github.com/judge0/compilers

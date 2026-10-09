@ECHO OFF

SETLOCAL
SET SPHINXBUILD=uv run sphinx-build
SET SOURCEDIR=source
SET BUILDDIR=_build
SET SPHINXOPTS=-E -a -W -n -T

IF "%1"=="" GOTO help
IF "%1"=="html" GOTO html
IF "%1"=="clean" GOTO clean
GOTO help

:html
%SPHINXBUILD% %SPHINXOPTS% -b html %SOURCEDIR% %BUILDDIR%\html
IF ERRORLEVEL 1 EXIT /B 1
GOTO end

:clean
IF EXIST %BUILDDIR% RMDIR /S /Q %BUILDDIR%
GOTO end

:help
ECHO Usage: make.bat ^<html^|clean^>

:end
ENDLOCAL

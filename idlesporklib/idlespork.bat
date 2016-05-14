@echo off
rem Start idlespork using the appropriate Python interpreter
set CURRDIR=%~dp0
start "idlespork" "%CURRDIR%..\..\..\pythonw.exe" "%CURRDIR%idlespork.pyw" %1 %2 %3 %4 %5 %6 %7 %8 %9

@echo off
setlocal
cd /d %~dp0
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://artifacts.elastic.co/downloads/beats/winlogbeat/winlogbeat-7.14.1-windows-x86_64.zip', 'c:\package.zip')"
mkdir C:\Tmp
Call :UnZipFile "C:\Tmp\" "c:\package.zip"
cd C:\Tmp
copy a:\{{winlogbeat_config}} C:\Tmp\winlogbeat.yml
Powershell.exe -executionpolicy remotesigned -File .\install-service-winlogbeat.ps1
exit /b

:UnZipFile <ExtractTo> <newzipfile>
set vbs="%temp%\_.vbs"
if exist %vbs% del /f /q %vbs%
>%vbs%  echo Set fso = CreateObject("Scripting.FileSystemObject")
>>%vbs% echo If NOT fso.FolderExists(%1) Then
>>%vbs% echo fso.CreateFolder(%1)
>>%vbs% echo End If
>>%vbs% echo set objShell = CreateObject("Shell.Application")
>>%vbs% echo set FilesInZip=objShell.NameSpace(%2).items
>>%vbs% echo objShell.NameSpace(%1).CopyHere(FilesInZip)
>>%vbs% echo Set fso = Nothing
>>%vbs% echo Set objShell = Nothing
cscript //nologo %vbs%
if exist %vbs% del /f /q %vbs%
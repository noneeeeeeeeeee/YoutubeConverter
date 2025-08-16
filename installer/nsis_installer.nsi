; filepath: c:\dev\Github\YoutubeConverter\installer\nsis_installer.nsi
!define APP_NAME "YoutubeConverter"
!define APP_PUBLISHER "noneeeeeeeeeee"
!define APP_VERSION "0.1.0"
!define INSTALL_DIR "$PROGRAMFILES64\${APP_NAME}"

OutFile "YoutubeConverter-Setup-${APP_VERSION}.exe"
InstallDir "${INSTALL_DIR}"
RequestExecutionLevel admin
Unicode true
ShowInstDetails show

Section "Install"
  SetOutPath "${INSTALL_DIR}"
  File /r "..\dist\YoutubeConverter\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}.lnk" "$INSTDIR\YoutubeConverter.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\${APP_NAME}.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
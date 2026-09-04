' Lanza REY Inventarios en modo navegador sin ventana de consola.
' Doble clic en este archivo para abrir http://localhost:8550

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

root = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = root & "\.venv\Scripts\pythonw.exe"
mainpy = root & "\main.py"

If Not fso.FileExists(pythonw) Then
  pythonw = root & "\.venv\Scripts\python.exe"
End If

If Not fso.FileExists(pythonw) Then
  MsgBox "No se encontro el Python del proyecto (.venv).", vbCritical, "REY Inventarios"
  WScript.Quit 1
End If

shell.Run """" & pythonw & """ """ & mainpy & """ --web", 0, False

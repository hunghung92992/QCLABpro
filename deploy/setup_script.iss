; --- INNO SETUP SCRIPT CHO QC LAB MANAGER (HOÀN THIỆN BL-003) ---
#define MyAppName "QC Lab Manager"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "HungLab"
#define MyAppExeName "QCLabManager.exe"
#define MyAppID "{A1B2C3D4-E5F6-7890-ABCD-1234567890AB}"

[Setup]
AppId={{#MyAppID}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Lùi ra 1 cấp để xuất file Setup.exe ra thư mục Output ở ngoài thư mục gốc
OutputDir=..\Output
OutputBaseFilename=QCLabManager_v{#MyAppVersion}_Setup
; Lùi ra 1 cấp để tìm đúng icon
SetupIconFile=..\app\assets\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; [QUAN TRỌNG] Dùng admin để ghi vào Program Files, nhưng app sẽ chạy ghi data vào AppData (không cần quyền)
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 1. BỘ CÀI CHƯƠNG TRÌNH (Phần mềm - Read Only)
; Dùng '..\dist\' để Inno Setup biết cần lùi ra ngoài thư mục deploy để tìm thư mục dist
Source: "..\dist\QCLabManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 2. DỮ LIỆU HỆ THỐNG (Database & Config mẫu - Writable)
; Đưa vào {localappdata} để khớp với Path Manager
; [THÊM] 'skipifsourcedoesntexist': Nếu máy dev của bạn hiện tại không có file Datauser.db ở thư mục gốc thì nó sẽ bỏ qua, không báo lỗi biên dịch.
Source: "..\Datauser.db"; DestDir: "{localappdata}\{#MyAppName}"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist
Source: "..\config.json"; DestDir: "{localappdata}\{#MyAppName}"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist

; 3. TẠO SẴN CẤU TRÚC THƯ MỤC (Dành cho Reports/Backups)
[Dirs]
Name: "{userdocs}\{#MyAppName}"
Name: "{userdocs}\{#MyAppName}\Reports"
Name: "{userdocs}\{#MyAppName}\Backups"
Name: "{userdocs}\{#MyAppName}\Attachments"
Name: "{localappdata}\{#MyAppName}\logs"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Sau khi cài xong, chạy app với quyền User thường (không cần Run as Admin)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Chỉ xóa các file tạm, log. KHÔNG xóa thư mục Database và Backups để bảo vệ dữ liệu bệnh viện
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}\logs\*"
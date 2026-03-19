; --- INNO SETUP SCRIPT CHO QC LAB MANAGER (PHIÊN BẢN NUITKA C++) ---
#define MyAppName "QC Lab Manager Pro"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "HungLab"
#define MyAppExeName "QCLabManager.exe"
#define MyAppID "A1B2C3D4-E5F6-7890-ABCD-1234567890AB"

[Setup]
; Sửa lại cú pháp ngoặc nhọn kép để Inno Setup không báo lỗi parse GUID
AppId={{{#MyAppID}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Xuất file Setup.exe ra thư mục "Output" nằm ngay trong thư mục "deploy"
OutputDir=Output
OutputBaseFilename=Setup_QCLabManager_v{#MyAppVersion}

; Lùi ra 1 cấp để tìm đúng icon gốc của dự án
SetupIconFile=..\app\assets\logo.ico

; [TỐI ƯU] Ép xung thuật toán nén để giảm dung lượng file cài đặt
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

; Dùng admin để ghi vào Program Files, nhưng app sẽ chạy ghi data vào AppData
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; [CẬP NHẬT QUAN TRỌNG]: Lấy nguồn từ thư mục Release của Nuitka
Source: "Release\QCLabManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; [CHỈNH SỬA KIẾN TRÚC TỪ TECH LEAD]: Đã vô hiệu hóa việc copy DB máy Dev.
; App sẽ tự gọi hàm run_bootstrap() sinh DB sạch tại AppData ở lần chạy đầu tiên!
; Source: "..\Datauser.db"; DestDir: "{localappdata}\{#MyAppName}"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist
; Source: "..\config.json"; DestDir: "{localappdata}\{#MyAppName}"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist

; TẠO SẴN CẤU TRÚC THƯ MỤC CHUẨN (Dành cho Reports/Backups)
[Dirs]
Name: "{userdocs}\{#MyAppName}"
Name: "{userdocs}\{#MyAppName}\Reports"
Name: "{userdocs}\{#MyAppName}\Backups"
Name: "{userdocs}\{#MyAppName}\Attachments"
Name: "{localappdata}\{#MyAppName}\logs"

[Icons]
; [TỐI ƯU] Gắn cứng IconFilename để icon hiển thị sắc nét trên mọi hệ điều hành
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app\assets\logo.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\app\assets\logo.ico"

[Run]
; Sau khi cài xong, chạy app với quyền User thường (không cần Run as Admin)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Chỉ xóa các file tạm, log. KHÔNG xóa thư mục Database và Backups để bảo vệ dữ liệu bệnh viện
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}\logs\*"
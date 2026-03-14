-- Giai đoạn 1: Khởi tạo Schema (001_init_schema.sql)
-- Tổng hợp 53 bảng (phiên bản v2) dựa trên toàn bộ mã nguồn và mô tả dự án.

-- Bật hỗ trợ khoá ngoại
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- =============================================================================
-- MODULE 1: CORE ADMIN (Users, Departments, Audit, Menu)
-- =============================================================================

-- Phòng ban (từ dept_service_sqlite.py)
CREATE TABLE IF NOT EXISTS department (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT UNIQUE NOT NULL,
    note   TEXT DEFAULT '',
    active INTEGER DEFAULT 1 -- Thêm cột active (từ mô tả)
);

-- Người dùng (từ user_admin.py & auth_util.py)
-- department ở đây lưu TEXT (tên phòng ban) để đơn giản, không dùng FK
CREATE TABLE IF NOT EXISTS users_ex (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash BLOB,
    salt          BLOB, -- (Dùng cho legacy SHA256, bcrypt đã bao gồm salt)
    role          TEXT DEFAULT 'VIEWER',
    department    TEXT,
    fullname      TEXT,
    is_active     INTEGER DEFAULT 1
);

-- Nhật ký hệ thống (từ audit_util.py)
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc      TEXT,
    actor       TEXT,
    action      TEXT,
    target      TEXT,
    before_json TEXT,
    after_json  TEXT,
    note        TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log (ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log (actor);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log (action);

-- Phân quyền menu (từ db_menu_visibility.py)
CREATE TABLE IF NOT EXISTS menu_visibility (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    menu_key TEXT NOT NULL,
    visible  INTEGER DEFAULT 1,
    UNIQUE(username, menu_key)
);

-- =============================================================================
-- MODULE 2: CATALOG (Analytes, Tests, Lots v2)
-- =============================================================================

-- Bảng gốc các chất phân tích (nếu cần)
CREATE TABLE IF NOT EXISTS analyte (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    unit       TEXT,
    department TEXT, -- (Trường này có thể không cần nếu dùng department_test)
    method     TEXT,
    active     INTEGER DEFAULT 1
);

-- Danh mục Test theo phòng ban (từ dept_service_sqlite.py)
CREATE TABLE IF NOT EXISTS department_test (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL,
    test_name     TEXT NOT NULL,
    unit          TEXT NOT NULL,
    analyte_id    INTEGER, -- (Link tới 'analyte' nếu cần)
    method        TEXT,    -- (Thêm từ mô tả)
    active        INTEGER DEFAULT 1, -- (Thêm từ mô tả)
    UNIQUE(department_id, test_name),
    FOREIGN KEY(department_id) REFERENCES department(id) ON DELETE CASCADE,
    FOREIGN KEY(analyte_id) REFERENCES analyte(id) ON DELETE SET NULL
);

-- Catalog mềm (từ qc_lot_v2_service.py)
CREATE TABLE IF NOT EXISTS lab_test_catalog (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    department   TEXT NOT NULL,
    test_name    TEXT NOT NULL,
    data_type    TEXT CHECK(data_type IN ('Quant','Semi','Qual')) DEFAULT 'Quant',
    default_unit TEXT,
    is_active    INTEGER DEFAULT 1,
    UNIQUE(department, test_name)
);

-- Bảng Header LOT (từ qc_lot_v2_service.py)
CREATE TABLE IF NOT EXISTS qc_lot (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL, -- (Tên bộ QC, ví dụ: "Lyphochek Assayed Chemistry")
    lot_no            TEXT NOT NULL, -- (Số LOT)
    manufactured_date TEXT,          -- YYYY-MM-DD
    expiry_date       TEXT,          -- YYYY-MM-DD
    department        TEXT,
    status            TEXT DEFAULT 'active', -- (active, dis)
    active            INTEGER DEFAULT 1,
    material_id       INTEGER,
    analyte_id        INTEGER,       -- (Dùng cho schema cũ nếu 1 lot 1 test)
    level             TEXT           -- (Dùng cho schema cũ nếu 1 lot 1 test)
);
CREATE INDEX IF NOT EXISTS idx_qc_lot_lot_no ON qc_lot (lot_no);
CREATE INDEX IF NOT EXISTS idx_qc_lot_department ON qc_lot (department);

-- Bảng Chi tiết LOT (Analyte/Target) (từ qc_lot_v2_service.py)
CREATE TABLE IF NOT EXISTS qc_lot_analyte (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id          INTEGER NOT NULL,
    department      TEXT,
    lab_test_id     INTEGER, -- (ID từ department_test)
    test_name       TEXT NOT NULL,
    level           TEXT,
    mean            REAL,
    sd              REAL,
    tea             REAL,
    note            TEXT,
    active          INTEGER DEFAULT 1,
    data_type       TEXT, -- (Quant, Semi, Qual)
    unit            TEXT,
    reference_range TEXT,
    category        TEXT,
    FOREIGN KEY(lot_id) REFERENCES qc_lot(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_qc_lot_analyte_lot ON qc_lot_analyte (lot_id);
CREATE INDEX IF NOT EXISTS idx_qc_lot_analyte_test ON qc_lot_analyte (test_name);

-- (Các bảng phụ trợ từ mô tả nếu cần - Bỏ qua nếu v2 không dùng)
-- CREATE TABLE IF NOT EXISTS qc_material (...);
-- CREATE TABLE IF NOT EXISTS qc_level (...);
-- CREATE TABLE IF NOT EXISTS qc_target (...); -- (v2 dùng qc_lot_analyte)


-- =============================================================================
-- MODULE 3: IQC (Nội kiểm v2)
-- =============================================================================

-- Bảng Phiên chạy IQC (từ iqc_service.py)
CREATE TABLE IF NOT EXISTS iqc_run (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date     TEXT,
    run_time     TEXT,
    department   TEXT,
    device       TEXT,
    user         TEXT,
    levels_count INTEGER,
    run_type     TEXT, -- (quant, semi, qual)
    note         TEXT  -- (Thêm từ mô tả)
);
CREATE INDEX IF NOT EXISTS idx_iqc_run_date ON iqc_run (run_date DESC);

-- Bảng Kết quả IQC (từ iqc_service.py)
CREATE TABLE IF NOT EXISTS iqc_result (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL,
    test_code     TEXT,
    level         TEXT,
    value         TEXT,    -- (Giá trị gốc dạng text)
    unit          TEXT,
    lot           TEXT,
    lot_expiry    TEXT,
    analyte_id    INTEGER,
    department    TEXT,
    result_type   TEXT,    -- (quant, semi, qual)
    value_num     REAL,    -- (Dùng cho quant)
    value_cat     TEXT,    -- (Dùng cho semi, vd: "+1")
    value_score   REAL,    -- (Dùng cho semi, vd: 1.0)
    value_bool    INTEGER, -- (Dùng cho qual, 0/1)
    expected_num  REAL,
    expected_cat  TEXT,
    expected_bool INTEGER,
    pass_fail     INTEGER, -- (0/1)
    sdi           REAL,    -- (Thêm từ mô tả)
    note          TEXT,    -- (Thêm từ mô tả)
    FOREIGN KEY(run_id) REFERENCES iqc_run(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_iqc_result_run_id ON iqc_result (run_id);
CREATE INDEX IF NOT EXISTS idx_iqc_result_test_code ON iqc_result (test_code);
CREATE INDEX IF NOT EXISTS idx_iqc_result_department ON iqc_result (department);

-- Lịch Nội kiểm (từ iqc_schedule_service.py)
CREATE TABLE IF NOT EXISTS iqc_schedule (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER,
    device_id     INTEGER,
    test_code     TEXT NOT NULL,
    level         INTEGER NOT NULL,
    freq          TEXT NOT NULL DEFAULT 'ndays', -- (daily, weekly, monthly, ndays)
    every_n       INTEGER NOT NULL DEFAULT 1,
    grace_days    INTEGER NOT NULL DEFAULT 0,
    hard_lock     INTEGER NOT NULL DEFAULT 0,
    last_run      TEXT, -- YYYY-MM-DD
    start_date    TEXT, -- (Thêm từ mô tả)
    end_date      TEXT, -- (Thêm từ mô tả)
    due_date      TEXT, -- (Thêm từ mô tả)
    lock_input    INTEGER, -- (Thêm từ mô tả)
    note          TEXT DEFAULT '',
    UNIQUE(department_id, device_id, test_code, level)
);
CREATE INDEX IF NOT EXISTS idx_iqc_schedule_key ON iqc_schedule (test_code, level, department_id, device_id);

-- =============================================================================
-- MODULE 4: DEVICES (Kết nối thiết bị)
-- =============================================================================

-- Quản lý thiết bị (từ device_admin.py)
CREATE TABLE IF NOT EXISTS devices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT UNIQUE,
    name            TEXT,
    model           TEXT,
    serial          TEXT, -- (serial_number từ mô tả)
    manufacturer    TEXT, -- (vendor từ mô tả)
    department_id   INTEGER,
    department_name TEXT,
    location        TEXT,
    status          TEXT,
    note            TEXT,
    conn_type       TEXT DEFAULT 'none', -- (tcp, serial)
    protocol        TEXT DEFAULT 'plain',
    ip              TEXT,
    port            INTEGER,
    serial_port     TEXT,
    baudrate        INTEGER,
    parity          TEXT,
    stopbits        INTEGER,
    is_enabled      INTEGER DEFAULT 1,
    last_heartbeat  TEXT,
    last_message_at TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(department_id) REFERENCES department(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_devices_dept_id ON devices (department_id);

-- Log tin nhắn thiết bị (từ device_service.py)
CREATE TABLE IF NOT EXISTS device_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   INTEGER NOT NULL,
    direction   TEXT NOT NULL, -- (IN/OUT)
    payload     BLOB NOT NULL, -- (raw_message)
    protocol    TEXT,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_devmsg_device_time ON device_messages (device_id, created_at DESC);

-- =============================================================================
-- MODULE 5: EQA (Ngoại kiểm)
-- =============================================================================

-- (Schema tổng hợp từ eqa_dao.py, eqa_schedule_tab.py và mô tả)

CREATE TABLE IF NOT EXISTS eqa_provider (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS eqa_program (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER,
    name        TEXT NOT NULL,
    code        TEXT, -- (Mã chương trình)
    FOREIGN KEY(provider_id) REFERENCES eqa_provider(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS eqa_device (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL, -- (Tên thiết bị dùng cho EQA)
    program_id  INTEGER,
    provider_id INTEGER,
    created_at  TEXT NOT NULL,
    FOREIGN KEY(program_id) REFERENCES eqa_program(id) ON DELETE SET NULL,
    FOREIGN KEY(provider_id) REFERENCES eqa_provider(id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_eqa_device_u ON eqa_device(name, program_id, provider_id);

CREATE TABLE IF NOT EXISTS eqa_round (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id   INTEGER,
    program_name TEXT,
    year         INTEGER,
    round_no     TEXT,
    device_name  TEXT,
    status       TEXT,
    created_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_eqa_round_key ON eqa_round (program_id, year, round_no);

CREATE TABLE IF NOT EXISTS eqa_sample (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id    INTEGER NOT NULL,
    sample_code TEXT,
    note        TEXT,
    FOREIGN KEY(round_id) REFERENCES eqa_round(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eqa_param_template (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL,
    analyte    TEXT,
    unit       TEXT,
    UNIQUE(program_id, analyte),
    FOREIGN KEY(program_id) REFERENCES eqa_program(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eqa_task (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    year          INTEGER,
    round_no      TEXT,
    provider_id   INTEGER,
    provider_name TEXT,
    program_id    INTEGER,
    program_name  TEXT,
    sample_plan   TEXT, -- (Tên mẫu, vd: "Sample A, B")
    device_name   TEXT,
    assigned_to   TEXT,
    start_date    TEXT,
    end_date      TEXT,
    due_date      TEXT,
    status        TEXT, -- (NEW, RUN, DONE, LATE)
    note          TEXT,
    created_at    TEXT,
    updated_at    TEXT,
    created_by    TEXT
);
CREATE INDEX IF NOT EXISTS idx_eqa_task_year ON eqa_task (year DESC, due_date ASC);

CREATE TABLE IF NOT EXISTS eqa_task_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL,
    ts         TEXT,
    actor      TEXT,
    action     TEXT,
    note       TEXT,
    FOREIGN KEY(task_id) REFERENCES eqa_task(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eqa_result (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id         INTEGER NOT NULL,
    sample_id        INTEGER,
    sample_code      TEXT,
    analyte          TEXT, -- (Tên do site đặt)
    unit             TEXT,
    result_site      TEXT, -- (Kết quả của lab)
    result_center    TEXT, -- (Kết quả của trung tâm)
    note             TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT,
    provider_analyte TEXT, -- (Tên do nhà CC đặt)
    provider_unit    TEXT,
    FOREIGN KEY(round_id) REFERENCES eqa_round(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_eqa_result_round ON eqa_result (round_id);

CREATE TABLE IF NOT EXISTS eqa_submission (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER,
    round_id    INTEGER,
    submit_date TEXT,
    actor       TEXT,
    status      TEXT, -- (Draft, Submitted, Acknowledged)
    file_path   TEXT,
    FOREIGN KEY(task_id) REFERENCES eqa_task(id),
    FOREIGN KEY(round_id) REFERENCES eqa_round(id)
);

-- =============================================================================
-- MODULE 6: LEGACY TABLES (Các bảng cũ từ qc_sample_db.py, nếu cần)
-- =============================================================================

-- Bảng này được tham chiếu bởi qc_sample_admin (container của v2)
-- Nó cũng là nền tảng của qc_service_sqlite (phiên bản 7/8 cột cũ)
CREATE TABLE IF NOT EXISTS qc_sample (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    analyte_id  INTEGER NOT NULL,
    level_name  TEXT NOT NULL,
    lot         TEXT,
    prod_date   TEXT,
    expiry_date TEXT,
    mean        REAL,
    sd          REAL,
    tea         REAL,
    unit        TEXT,
    department  TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    UNIQUE(analyte_id, level_name, lot),
    FOREIGN KEY(analyte_id) REFERENCES analyte(id)
);

-- Bảng này được tham chiếu bởi iqc_service.py (phiên bản cũ)
CREATE TABLE IF NOT EXISTS qc_run (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id     INTEGER,
    run_ts            TEXT NOT NULL,
    operator          TEXT,
    operator_fullname TEXT
);

CREATE TABLE IF NOT EXISTS qc_result (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    qc_run_id    INTEGER NOT NULL,
    qc_level_id  INTEGER,
    qc_sample_id INTEGER,
    value        REAL NOT NULL,
    created_at   TEXT NOT NULL
);


COMMIT;
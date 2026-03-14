-- 003_add_sort_order.sql
-- Bổ sung cột sắp xếp thứ tự cho bảng chi tiết analyte
PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

ALTER TABLE qc_lot_analyte ADD COLUMN sort_order INTEGER DEFAULT 0;

COMMIT;

PRAGMA foreign_keys=ON;
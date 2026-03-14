-- Thêm cột data_type vào bảng cấu hình xét nghiệm của phòng ban
ALTER TABLE department_test
ADD COLUMN data_type TEXT CHECK(data_type IN ('Quant','Semi','Qual')) DEFAULT 'Quant';
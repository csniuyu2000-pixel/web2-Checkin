-- 日签：MySQL 建库建表（utf8mb4，created_at 为 DATETIME）
-- 用法示例：
--   mysql -u root -p < 03_schema_mysql.sql

CREATE DATABASE IF NOT EXISTS riqian
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE riqian;

DROP TABLE IF EXISTS checkins;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('student', 'admin') NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE checkins (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(20) NOT NULL,
  location VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL,
  user_id INT NULL,
  PRIMARY KEY (id),
  KEY idx_checkins_created_at (created_at),
  KEY idx_checkins_name (name),
  KEY idx_checkins_user_id (user_id),
  CONSTRAINT fk_checkins_user
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

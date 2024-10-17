mysqldump -h127.0.0.1 -P3306 -uroot -p'root' --databases beancount-trans > beancount_trans.sql  # 备份
mysql -h127.0.0.1 -P3306 -uroot -p'root' -o beancount-trans < beancount_trans.sql  # 恢复

-- MySQL dump 10.13  Distrib 8.2.0, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: beancount-trans
-- ------------------------------------------------------
-- Server version	8.0.26

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `beancount-trans`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `beancount-trans` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `beancount-trans`;

--
-- Table structure for table `account_account`
--

DROP TABLE IF EXISTS `account_account`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `account_account` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created` datetime(6) NOT NULL,
  `modified` datetime(6) NOT NULL,
  `date` date NOT NULL,
  `status` varchar(8) COLLATE utf8mb4_general_ci NOT NULL,
  `account` varchar(64) COLLATE utf8mb4_general_ci NOT NULL,
  `currency` varchar(16) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `note` varchar(16) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `account_type` varchar(16) COLLATE utf8mb4_general_ci NOT NULL,
  `owner_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `account_account_owner_id_00d11601_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `account_account_owner_id_00d11601_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `account_account`
--

LOCK TABLES `account_account` WRITE;
/*!40000 ALTER TABLE `account_account` DISABLE KEYS */;
/*!40000 ALTER TABLE `account_account` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add content type',4,'add_contenttype'),(14,'Can change content type',4,'change_contenttype'),(15,'Can delete content type',4,'delete_contenttype'),(16,'Can view content type',4,'view_contenttype'),(17,'Can add session',5,'add_session'),(18,'Can change session',5,'change_session'),(19,'Can delete session',5,'delete_session'),(20,'Can view session',5,'view_session'),(21,'Can add 资产映射',6,'add_assets'),(22,'Can change 资产映射',6,'change_assets'),(23,'Can delete 资产映射',6,'delete_assets'),(24,'Can view 资产映射',6,'view_assets'),(25,'Can add 支出映射',7,'add_expense'),(26,'Can change 支出映射',7,'change_expense'),(27,'Can delete 支出映射',7,'delete_expense'),(28,'Can view 支出映射',7,'view_expense'),(29,'Can add 收入映射',8,'add_income'),(30,'Can change 收入映射',8,'change_income'),(31,'Can delete 收入映射',8,'delete_income'),(32,'Can view 收入映射',8,'view_income'),(33,'Can add 账本账户',9,'add_account'),(34,'Can change 账本账户',9,'change_account'),(35,'Can delete 账本账户',9,'delete_account'),(36,'Can view 账本账户',9,'view_account'),(37,'Can add 用户',10,'add_user'),(38,'Can change 用户',10,'change_user'),(39,'Can delete 用户',10,'delete_user'),(40,'Can view 用户',10,'view_user');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_general_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `first_name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `last_name` varchar(150) COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_general_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `mobile` varchar(11) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `mobile` (`mobile`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
INSERT INTO `auth_user` VALUES (1,'pbkdf2_sha256$720000$ZZCeMv4wrJh30XkfLvqZFm$PKVT7xAKWyKHzmREk3IINFBiHgGjy6XQ6ee8/kQvrsM=','2024-04-06 11:53:00.000000',1,'admin','','','admin@example.com',1,1,'2024-04-06 11:45:00.000000','11111111111');
/*!40000 ALTER TABLE `auth_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
INSERT INTO `auth_user_user_permissions` VALUES (1,1,1),(2,1,2),(3,1,3),(4,1,4),(5,1,5),(6,1,6),(7,1,7),(8,1,8),(9,1,9),(10,1,10),(11,1,11),(12,1,12),(13,1,13),(14,1,14),(15,1,15),(16,1,16),(17,1,17),(18,1,18),(19,1,19),(20,1,20),(21,1,21),(22,1,22),(23,1,23),(24,1,24),(25,1,25),(26,1,26),(27,1,27),(28,1,28),(29,1,29),(30,1,30),(31,1,31),(32,1,32),(33,1,33),(34,1,34),(35,1,35),(36,1,36),(37,1,37),(38,1,38),(39,1,39),(40,1,40);
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_general_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_general_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext COLLATE utf8mb4_general_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
INSERT INTO `django_admin_log` VALUES (1,'2024-04-06 11:54:13.323202','1','admin',2,'[{\"changed\": {\"fields\": [\"User permissions\", \"Last login\"]}}]',10,1);
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (9,'account','account'),(1,'admin','logentry'),(3,'auth','group'),(2,'auth','permission'),(4,'contenttypes','contenttype'),(5,'sessions','session'),(6,'translate','assets'),(7,'translate','expense'),(8,'translate','income'),(10,'users','user');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2024-04-06 11:44:40.381569'),(2,'contenttypes','0002_remove_content_type_name','2024-04-06 11:44:42.786012'),(3,'auth','0001_initial','2024-04-06 11:44:49.840482'),(4,'auth','0002_alter_permission_name_max_length','2024-04-06 11:44:51.295767'),(5,'auth','0003_alter_user_email_max_length','2024-04-06 11:44:51.396404'),(6,'auth','0004_alter_user_username_opts','2024-04-06 11:44:51.505345'),(7,'auth','0005_alter_user_last_login_null','2024-04-06 11:44:51.630793'),(8,'auth','0006_require_contenttypes_0002','2024-04-06 11:44:51.735532'),(9,'auth','0007_alter_validators_add_error_messages','2024-04-06 11:44:51.853392'),(10,'auth','0008_alter_user_username_max_length','2024-04-06 11:44:52.002760'),(11,'auth','0009_alter_user_last_name_max_length','2024-04-06 11:44:52.203129'),(12,'auth','0010_alter_group_name_max_length','2024-04-06 11:44:52.446967'),(13,'auth','0011_update_proxy_permissions','2024-04-06 11:44:52.626667'),(14,'auth','0012_alter_user_first_name_max_length','2024-04-06 11:44:52.738416'),(15,'users','0001_initial','2024-04-06 11:45:01.248675'),(16,'account','0001_initial','2024-04-06 11:45:03.464957'),(17,'admin','0001_initial','2024-04-06 11:45:07.193755'),(18,'admin','0002_logentry_remove_auto_add','2024-04-06 11:45:07.319468'),(19,'admin','0003_logentry_add_action_flag_choices','2024-04-06 11:45:07.422008'),(20,'sessions','0001_initial','2024-04-06 11:45:08.720107'),(21,'translate','0001_initial','2024-04-06 11:45:09.879889'),(22,'translate','0002_initial','2024-04-06 11:45:13.295982'),(23,'translate','0003_remove_expense_payee_order','2024-04-06 11:45:15.131335'),(24,'translate','0004_alter_assets_options_remove_assets_income_and_more','2024-04-06 11:45:19.727559'),(25,'translate','0005_remove_expense_classification_remove_expense_tag','2024-04-06 11:45:22.660566');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_general_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_general_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `maps_assets`
--

DROP TABLE IF EXISTS `maps_assets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `maps_assets` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created` datetime(6) NOT NULL,
  `modified` datetime(6) NOT NULL,
  `key` varchar(16) COLLATE utf8mb4_general_ci NOT NULL,
  `full` varchar(16) COLLATE utf8mb4_general_ci NOT NULL,
  `owner_id` bigint NOT NULL,
  `assets` varchar(64) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `maps_assets_owner_id_c6403b26_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `maps_assets_owner_id_c6403b26_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_assets`
--

LOCK TABLES `maps_assets` WRITE;
/*!40000 ALTER TABLE `maps_assets` DISABLE KEYS */;
INSERT INTO `maps_assets` VALUES (1,'2024-04-06 11:50:43.203910','2024-04-06 11:50:43.203956','5522','中国建设银行储蓄卡(5522)',1,'Assets:Savings:Bank:CCB:C5522'),(2,'2024-04-06 11:50:43.302020','2024-04-06 11:50:43.302047','6428','中信银行信用卡(6428)',1,'Liabilities:CreditCard:Bank:CITIC:C6428'),(3,'2024-04-06 11:50:43.386417','2024-04-06 11:50:43.386480','零钱通','微信零钱通',1,'Assets:Savings:Web:WechatFund'),(4,'2024-04-06 11:50:43.511946','2024-04-06 11:50:43.512013','零钱','微信零钱',1,'Assets:Savings:Web:WechatPay'),(5,'2024-04-06 11:50:43.795316','2024-04-06 11:50:43.795355','/','微信零钱',1,'Assets:Savings:Web:WechatPay'),(6,'2024-04-06 11:50:43.903631','2024-04-06 11:50:43.903701','8837','中国招商银行储蓄卡(8837)',1,'Assets:Savings:Bank:CMB:C8837'),(7,'2024-04-06 11:50:44.011975','2024-04-06 11:50:44.012047','1746','宁波银行储蓄卡(1746)',1,'Assets:Savings:Bank:NBCB:C1746'),(8,'2024-04-06 11:50:44.112803','2024-04-06 11:50:44.112845','8273','中国农业银行储蓄卡(8273)',1,'Assets:Savings:Bank:ABC:C8273'),(9,'2024-04-06 11:50:44.263742','2024-04-06 11:50:44.263815','7651','中国工商银行储蓄卡(7651)',1,'Assets:Savings:Bank:ICBC:C7651'),(10,'2024-04-06 11:50:44.340051','2024-04-06 11:50:44.340118','5244','中国工商银行储蓄卡(5244)',1,'Assets:Savings:Bank:ICBC:C5244'),(11,'2024-04-06 11:50:44.414478','2024-04-06 11:50:44.414500','5636','华夏银行储蓄卡(5636)',1,'Assets:Savings:Bank:HXB:C5636'),(12,'2024-04-06 11:50:44.502744','2024-04-06 11:50:44.502766','余额宝','支付宝余额宝',1,'Assets:Savings:Web:AliFund'),(13,'2024-04-06 11:50:44.607021','2024-04-06 11:50:44.607044','余额','支付宝余额',1,'Assets:Savings:Web:AliPay'),(14,'2024-04-06 11:50:44.691136','2024-04-06 11:50:44.691172','戴某轩','小荷包(戴某轩)',1,'Assets:Savings:Web:XiaoHeBao:DaiMouXuan'),(15,'2024-04-06 11:50:44.777954','2024-04-06 11:50:44.777982','账户余额','支付宝余额',1,'Assets:Savings:Web:AliPay'),(16,'2024-04-06 11:50:44.874888','2024-04-06 11:50:44.874915','花呗','支付宝花呗',1,'Liabilities:CreditCard:Web:HuaBei'),(17,'2024-04-06 11:50:44.961180','2024-04-06 11:50:44.961205','4523','中国招商银行信用卡(4523)',1,'Liabilities:CreditCard:Bank:CMB:C4523'),(18,'2024-04-06 11:50:45.069472','2024-04-06 11:50:45.069495','8313','中国招商银行信用卡(8313)',1,'Liabilities:CreditCard:Bank:CMB:C8313'),(19,'2024-04-06 11:50:45.169450','2024-04-06 11:50:45.169474','9813','中国招商银行信用卡(9813)',1,'Liabilities:CreditCard:Bank:CMB:C9813'),(20,'2024-04-06 11:50:45.269508','2024-04-06 11:50:45.269552','0005','浙江农商银行储蓄卡(0005)',1,'Assets:Savings:Bank:ZJRCUB:C0005'),(21,'2024-04-06 11:50:45.369702','2024-04-06 11:50:45.369728','0814','中国银行储蓄卡(0814)',1,'Assets:Savings:Bank:BOC:C0814');
/*!40000 ALTER TABLE `maps_assets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `maps_expense`
--

DROP TABLE IF EXISTS `maps_expense`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `maps_expense` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created` datetime(6) NOT NULL,
  `modified` datetime(6) NOT NULL,
  `key` varchar(16) COLLATE utf8mb4_general_ci NOT NULL,
  `payee` varchar(8) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `expend` varchar(64) COLLATE utf8mb4_general_ci NOT NULL,
  `owner_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `maps_expense_owner_id_d327d8f9_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `maps_expense_owner_id_d327d8f9_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=120 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_expense`
--

LOCK TABLES `maps_expense` WRITE;
/*!40000 ALTER TABLE `maps_expense` DISABLE KEYS */;
INSERT INTO `maps_expense` VALUES (1,'2024-04-06 11:50:23.128324','2024-04-06 11:50:23.128353','蜜雪冰城','蜜雪冰城','Expenses:Food:DrinkFruit',1),(2,'2024-04-06 11:50:23.226042','2024-04-06 11:50:23.226117','停车','','Expenses:TransPort:Private:Park',1),(3,'2024-04-06 11:50:23.326178','2024-04-06 11:50:23.326278','浙C','','Expenses:TransPort:Private:Park',1),(4,'2024-04-06 11:50:23.712929','2024-04-06 11:50:23.713007','鲜花','','Expenses:Culture',1),(5,'2024-04-06 11:50:23.821604','2024-04-06 11:50:23.821672','古茗','古茗','Expenses:Food:DrinkFruit',1),(6,'2024-04-06 11:50:23.888472','2024-04-06 11:50:23.888537','益味坊','益味坊','Expenses:Food:Breakfast',1),(7,'2024-04-06 11:50:24.064774','2024-04-06 11:50:24.064836','塔斯汀','塔斯汀','Expenses:Food',1),(8,'2024-04-06 11:50:24.151239','2024-04-06 11:50:24.151305','十足','十足','Expenses:Food',1),(9,'2024-04-06 11:50:24.251120','2024-04-06 11:50:24.251186','一点点','一点点','Expenses:Food:DrinkFruit',1),(10,'2024-04-06 11:50:24.351323','2024-04-06 11:50:24.351394','luckin','瑞幸','Expenses:Food:DrinkFruit',1),(11,'2024-04-06 11:50:24.465910','2024-04-06 11:50:24.465978','娘娘大人','娘娘大人','Expenses:Food',1),(12,'2024-04-06 11:50:24.574711','2024-04-06 11:50:24.574780','老婆大人','老婆大人','Assets:Savings:Recharge:LaoPoDaRen',1),(13,'2024-04-06 11:50:24.691655','2024-04-06 11:50:24.691716','茶百道','茶百道','Expenses:Food:DrinkFruit',1),(14,'2024-04-06 11:50:24.766357','2024-04-06 11:50:24.766394','京东','京东','Expenses:Shopping',1),(15,'2024-04-06 11:50:24.858720','2024-04-06 11:50:24.858782','包月','','Expenses:Culture:Subscription',1),(16,'2024-04-06 11:50:25.050719','2024-04-06 11:50:25.050783','正新鸡排','正新鸡排','Expenses:Food',1),(17,'2024-04-06 11:50:25.142685','2024-04-06 11:50:25.142748','奇虎智能','360','Expenses:Shopping:Digital',1),(18,'2024-04-06 11:50:25.309544','2024-04-06 11:50:25.309608','Petal On','华为','Expenses:Culture:Subscription',1),(19,'2024-04-06 11:50:25.434496','2024-04-06 11:50:25.434559','药房','','Expenses:Health:Medical',1),(20,'2024-04-06 11:50:25.576816','2024-04-06 11:50:25.576877','药店','','Expenses:Health:Medical',1),(21,'2024-04-06 11:50:25.685948','2024-04-06 11:50:25.685973','医院','','Expenses:Health',1),(22,'2024-04-06 11:50:25.963067','2024-04-06 11:50:25.963096','餐饮','','Expenses:Food',1),(23,'2024-04-06 11:50:26.193020','2024-04-06 11:50:26.193101','食品','','Expenses:Food',1),(24,'2024-04-06 11:50:26.333858','2024-04-06 11:50:26.333884','深圳市腾讯天游科技有限公司','','Expenses:Culture:Entertainment',1),(25,'2024-04-06 11:50:26.494294','2024-04-06 11:50:26.494316','水果','','Expenses:Food:DrinkFruit',1),(26,'2024-04-06 11:50:26.569445','2024-04-06 11:50:26.569469','早餐','','Expenses:Food:Breakfast',1),(27,'2024-04-06 11:50:26.644741','2024-04-06 11:50:26.644763','充电','','Expenses:TransPort:Private:Fuel',1),(28,'2024-04-06 11:50:26.725447','2024-04-06 11:50:26.725470','加油','','Expenses:TransPort:Private:Fuel',1),(29,'2024-04-06 11:50:26.825526','2024-04-06 11:50:26.825550','瑞安市供电局','国家电网','Expenses:Home:Recharge',1),(30,'2024-04-06 11:50:26.925585','2024-04-06 11:50:26.925608','ETC','','Expenses:TransPort:Public',1),(31,'2024-04-06 11:50:27.025528','2024-04-06 11:50:27.025552','华为终端有限公司','华为','Expenses:Shopping:Digital',1),(32,'2024-04-06 11:50:27.125534','2024-04-06 11:50:27.125556','饿了么','饿了么','Expenses:Food',1),(33,'2024-04-06 11:50:27.225709','2024-04-06 11:50:27.225743','美团平台商户','美团','Expenses:Food',1),(34,'2024-04-06 11:50:27.419069','2024-04-06 11:50:27.419108','地铁','','Expenses:TransPort:Public',1),(35,'2024-04-06 11:50:27.606339','2024-04-06 11:50:27.606402','国网智慧车联网','国家电网','Expenses:TransPort:Private:Fuel',1),(36,'2024-04-06 11:50:27.681545','2024-04-06 11:50:27.681609','肯德基','肯德基','Expenses:Food',1),(37,'2024-04-06 11:50:27.765433','2024-04-06 11:50:27.765496','华为','华为','Expenses:Shopping',1),(38,'2024-04-06 11:50:27.848738','2024-04-06 11:50:27.848806','沙县小吃','沙县小吃','Expenses:Food',1),(39,'2024-04-06 11:50:27.934829','2024-04-06 11:50:27.934897','一鸣','一鸣','Expenses:Food',1),(40,'2024-04-06 11:50:28.093109','2024-04-06 11:50:28.093179','之上','之上','Expenses:Food',1),(41,'2024-04-06 11:50:28.182121','2024-04-06 11:50:28.182149','大疆','','Expenses:Shopping:Digital',1),(42,'2024-04-06 11:50:28.274930','2024-04-06 11:50:28.275002','12306','12306','Expenses:TransPort:Public',1),(43,'2024-04-06 11:50:28.358595','2024-04-06 11:50:28.358664','阿里云','阿里云','Expenses:Culture:Subscription',1),(44,'2024-04-06 11:50:28.560100','2024-04-06 11:50:28.560174','电影','','Expenses:Culture:Entertainment',1),(45,'2024-04-06 11:50:28.668114','2024-04-06 11:50:28.668194','火车票','','Expenses:TransPort:Public',1),(46,'2024-04-06 11:50:28.844075','2024-04-06 11:50:28.844142','高铁','','Expenses:TransPort:Public',1),(47,'2024-04-06 11:50:28.926718','2024-04-06 11:50:28.926749','机票','','Expenses:TransPort:Public',1),(48,'2024-04-06 11:50:29.059840','2024-04-06 11:50:29.059907','医疗','','Expenses:Health',1),(49,'2024-04-06 11:50:29.175718','2024-04-06 11:50:29.175746','医生','','Expenses:Health',1),(50,'2024-04-06 11:50:29.303370','2024-04-06 11:50:29.303435','医用','','Expenses:Health',1),(51,'2024-04-06 11:50:29.445514','2024-04-06 11:50:29.445578','小吃','','Expenses:Food',1),(52,'2024-04-06 11:50:29.604221','2024-04-06 11:50:29.604287','餐厅','','Expenses:Food',1),(53,'2024-04-06 11:50:29.679435','2024-04-06 11:50:29.679506','小食','','Expenses:Food',1),(54,'2024-04-06 11:50:29.760032','2024-04-06 11:50:29.760101','旗舰店','淘宝','Expenses:Shopping',1),(55,'2024-04-06 11:50:29.859901','2024-04-06 11:50:29.859967','粮粮驾到','粮粮驾到','Assets:Savings:Recharge:LiangLiangJiaDao',1),(56,'2024-04-06 11:50:29.968235','2024-04-06 11:50:29.968304','中国石油','中国石油','Expenses:TransPort:Private:Fuel',1),(57,'2024-04-06 11:50:30.068334','2024-04-06 11:50:30.068408','酒店','','Expenses:Culture',1),(58,'2024-04-06 11:50:30.168361','2024-04-06 11:50:30.168435','某义','老婆','Expenses:Relationship',1),(59,'2024-04-06 11:50:30.267524','2024-04-06 11:50:30.267559','高德','高德','Expenses:TransPort:Public',1),(60,'2024-04-06 11:50:30.373506','2024-04-06 11:50:30.373574','烟酒','','Expenses:Food:DrinkFruit',1),(61,'2024-04-06 11:50:30.606742','2024-04-06 11:50:30.606800','理发','','Expenses:Shopping:Makeup',1),(62,'2024-04-06 11:50:30.707428','2024-04-06 11:50:30.707500','美发','','Expenses:Shopping:Makeup',1),(63,'2024-04-06 11:50:30.791681','2024-04-06 11:50:30.791753','美容','','Expenses:Shopping:Makeup',1),(64,'2024-04-06 11:50:30.890446','2024-04-06 11:50:30.890472','华莱士','华莱士','Expenses:Food',1),(65,'2024-04-06 11:50:30.999094','2024-04-06 11:50:30.999129','晚餐','','Expenses:Food:Dinner',1),(66,'2024-04-06 11:50:31.107797','2024-04-06 11:50:31.107820','午餐','','Expenses:Food:Lunch',1),(67,'2024-04-06 11:50:31.224966','2024-04-06 11:50:31.224992','新时沏','新时沏','Expenses:Food:DrinkFruit',1),(68,'2024-04-06 11:50:31.376066','2024-04-06 11:50:31.376091','得物','得物','Expenses:Shopping',1),(69,'2024-04-06 11:50:31.503739','2024-04-06 11:50:31.503894','拼多多','拼多多','Expenses:Shopping',1),(70,'2024-04-06 11:50:31.611106','2024-04-06 11:50:31.611165','移动','中国移动','Assets:Savings:Recharge:Operator:Mobile:C6428',1),(71,'2024-04-06 11:50:31.688367','2024-04-06 11:50:31.688435','电信','中国电信','Assets:Savings:Recharge:Operator:Telecom:C6428',1),(72,'2024-04-06 11:50:31.795035','2024-04-06 11:50:31.795084','联通','中国联通','Assets:Savings:Recharge:Operator:Unicom:C6428',1),(73,'2024-04-06 11:50:31.903148','2024-04-06 11:50:31.903172','深圳市腾讯计算机系统有限公司','','Expenses:Culture',1),(74,'2024-04-06 11:50:31.978483','2024-04-06 11:50:31.978506','胖哥俩','胖哥俩','Expenses:Food',1),(75,'2024-04-06 11:50:32.060051','2024-04-06 11:50:32.060145','服装','','Expenses:Shopping:Clothing',1),(76,'2024-04-06 11:50:32.168408','2024-04-06 11:50:32.168476','衣服','','Expenses:Shopping:Clothing',1),(77,'2024-04-06 11:50:32.260071','2024-04-06 11:50:32.260134','裤子','','Expenses:Shopping:Clothing',1),(78,'2024-04-06 11:50:32.349516','2024-04-06 11:50:32.349580','鞋子','','Expenses:Shopping:Clothing',1),(79,'2024-04-06 11:50:32.521912','2024-04-06 11:50:32.521937','袜子','','Expenses:Shopping:Clothing',1),(80,'2024-04-06 11:50:32.630425','2024-04-06 11:50:32.630448','华为软件技术有限公司','华为','Expenses:Culture:Subscription',1),(81,'2024-04-06 11:50:32.688824','2024-04-06 11:50:32.688849','淘宝','淘宝','Expenses:Shopping',1),(82,'2024-04-06 11:50:32.825995','2024-04-06 11:50:32.826040','医保','','Expenses:Health',1),(83,'2024-04-06 11:50:32.915270','2024-04-06 11:50:32.915336','自动续费','','Expenses:Culture:Subscription',1),(84,'2024-04-06 11:50:32.997915','2024-04-06 11:50:32.997941','诊疗','','Expenses:Health',1),(85,'2024-04-06 11:50:33.073866','2024-04-06 11:50:33.073940','卫生','','Expenses:Health',1),(86,'2024-04-06 11:50:33.161165','2024-04-06 11:50:33.161234','统一公共支付平台','','Expenses:Government',1),(87,'2024-04-06 11:50:33.277939','2024-04-06 11:50:33.278005','彩票','','Expenses:Culture',1),(88,'2024-04-06 11:50:33.450302','2024-04-06 11:50:33.450364','超市','','Expenses:Shopping',1),(89,'2024-04-06 11:50:33.642969','2024-04-06 11:50:33.643036','大润发','','Expenses:Shopping',1),(90,'2024-04-06 11:50:33.718201','2024-04-06 11:50:33.718270','便利店','','Expenses:Shopping',1),(91,'2024-04-06 11:50:33.825901','2024-04-06 11:50:33.825967','兰州拉面','兰州拉面','Expenses:Food',1),(92,'2024-04-06 11:50:33.901168','2024-04-06 11:50:33.901248','供水','国家水网','Expenses:Home:Recharge',1),(93,'2024-04-06 11:50:34.001459','2024-04-06 11:50:34.001524','绝味鸭脖','绝味鸭脖','Expenses:Food',1),(94,'2024-04-06 11:50:34.085069','2024-04-06 11:50:34.085137','舒活食品','一鸣','Assets:Savings:Recharge:YiMing',1),(95,'2024-04-06 11:50:34.178188','2024-04-06 11:50:34.178315','抖音生活服务','抖音','Expenses:Food',1),(96,'2024-04-06 11:50:34.367505','2024-04-06 11:50:34.367531','医药','','Expenses:Health',1),(97,'2024-04-06 11:50:34.562415','2024-04-06 11:50:34.562482','饮料','','Expenses:Food:DrinkFruit',1),(98,'2024-04-06 11:50:34.695945','2024-04-06 11:50:34.696006','抖音月付','抖音','Liabilities:CreditCard:Web:DouYin',1),(99,'2024-04-06 11:50:34.778047','2024-04-06 11:50:34.778113','公益','','Expenses:Culture',1),(100,'2024-04-06 11:50:34.879885','2024-04-06 11:50:34.879949','等多件','','Expenses:Shopping',1),(101,'2024-04-06 11:50:34.961379','2024-04-06 11:50:34.961456','喜茶','喜茶','Expenses:Food:DrinkFruit',1),(102,'2024-04-06 11:50:35.046329','2024-04-06 11:50:35.046357','支付宝小荷包(戴某轩)','','Assets:Savings:Web:XiaoHeBao:DaiMouXuan',1),(103,'2024-04-06 11:50:35.147368','2024-04-06 11:50:35.147429','倍耐力','','Expenses:TransPort:Private',1),(104,'2024-04-06 11:50:35.269936','2024-04-06 11:50:35.270003','娱乐','','Expenses:Culture',1),(105,'2024-04-06 11:50:35.377379','2024-04-06 11:50:35.377406','上海拉扎斯信息科技有限公司','','Expenses:Food',1),(106,'2024-04-06 11:50:35.556548','2024-04-06 11:50:35.556611','夜宵','','Expenses:Food:Dinner',1),(107,'2024-04-06 11:50:35.698718','2024-04-06 11:50:35.698780','打车','','Expenses:TransPort:Public',1),(108,'2024-04-06 11:50:35.798994','2024-04-06 11:50:35.799054','抖音电商','抖音','Expenses:Shopping',1),(109,'2024-04-06 11:50:35.882645','2024-04-06 11:50:35.882708','商城','','Expenses:Shopping',1),(110,'2024-04-06 11:50:35.978495','2024-04-06 11:50:35.978574','保险','','Expenses:Finance:Insurance',1),(111,'2024-04-06 11:50:36.086426','2024-04-06 11:50:36.086499','寄件','','Expenses:Home:Single',1),(112,'2024-04-06 11:50:36.183479','2024-04-06 11:50:36.183540','书店','','Expenses:Culture',1),(113,'2024-04-06 11:50:36.278142','2024-04-06 11:50:36.278202','外卖','','Expenses:Food',1),(114,'2024-04-06 11:50:36.392697','2024-04-06 11:50:36.392772','滴滴出行','','Expenses:TransPort:Public',1),(115,'2024-04-06 11:50:36.693046','2024-04-06 11:50:36.693113','公交','','Expenses:TransPort:Public',1),(116,'2024-04-06 11:50:36.776563','2024-04-06 11:50:36.776629','航空','','Expenses:TransPort:Public',1),(117,'2024-04-06 11:50:36.861636','2024-04-06 11:50:36.861703','储值','','Assets:Savings:Recharge',1),(118,'2024-04-06 11:50:36.978184','2024-04-06 11:50:36.978251','出行','','Expenses:TransPort:Public',1),(119,'2024-04-06 11:50:37.085800','2024-04-06 11:50:37.085863','下午茶','','Expenses:Food',1);
/*!40000 ALTER TABLE `maps_expense` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `maps_income`
--

DROP TABLE IF EXISTS `maps_income`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `maps_income` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created` datetime(6) NOT NULL,
  `modified` datetime(6) NOT NULL,
  `key` varchar(16) COLLATE utf8mb4_general_ci NOT NULL,
  `payer` varchar(8) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `income` varchar(64) COLLATE utf8mb4_general_ci NOT NULL,
  `owner_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `maps_income_owner_id_72c1c0ab_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `maps_income_owner_id_72c1c0ab_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_income`
--

LOCK TABLES `maps_income` WRITE;
/*!40000 ALTER TABLE `maps_income` DISABLE KEYS */;
INSERT INTO `maps_income` VALUES (1,'2024-04-06 11:50:37.153392','2024-04-06 11:50:37.153416','红包',NULL,'Income:Receivables:RedPacket',1),(2,'2024-04-06 11:50:37.286424','2024-04-06 11:50:37.286493','某义','老婆','Liabilities:Payables:Personal:LaoPo',1),(3,'2024-04-06 11:50:37.386650','2024-04-06 11:50:37.386717','小荷包',NULL,'Assets:Savings:Web:XiaoHeBao',1),(4,'2024-04-06 11:50:37.612024','2024-04-06 11:50:37.612087','老婆','老婆','Liabilities:Payables:Personal:LaoPo',1),(5,'2024-04-06 11:50:37.738555','2024-04-06 11:50:37.738623','戴某轩',NULL,'Assets:Savings:Web:XiaoHeBao:DaiMouXuan',1),(6,'2024-04-06 11:50:37.805534','2024-04-06 11:50:37.805602','收钱码经营版收款',NULL,'Income:Business',1),(7,'2024-04-06 11:50:37.872398','2024-04-06 11:50:37.872466','出行账户余额提现',NULL,'Income:Sideline:DiDi',1);
/*!40000 ALTER TABLE `maps_income` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-04-06 13:40:10

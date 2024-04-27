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
  `status` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `currency` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `note` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `account_type` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `owner_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `account_account_owner_id_00d11601_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `account_account_owner_id_00d11601_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `account_account`
--

LOCK TABLES `account_account` WRITE;
/*!40000 ALTER TABLE `account_account` DISABLE KEYS */;
INSERT INTO `account_account` VALUES (1,'2023-10-22 10:04:20.370341','2023-10-22 12:43:57.553372','2022-01-01','open','Assets:Savings:Web:AliPay','CNY','三方支付(支付宝)','assets',1),(2,'2023-10-22 15:53:40.658553','2023-10-22 15:53:40.658590','2023-10-14','open','1','1','1','assets',1),(3,'2023-10-22 15:54:47.693652','2023-10-22 15:54:47.693684','2022-01-01','open','Assets:Savings:Web:AliPay1','CNY','三方支付(支付宝)','assets',1),(4,'2023-10-22 16:22:35.247844','2023-10-22 16:22:35.247879','2022-01-01','open','Assets:Savings:Web:AliPay3','CNY','三方支付(支付宝)','assets',1),(5,'2023-10-22 17:31:12.324198','2023-10-22 17:31:12.324419','2022-01-01','open','Assets:Savings:Web:AliPay4','CNY','三方支付(支付宝)','assets',1),(6,'2023-10-22 21:41:12.277074','2023-10-22 21:41:12.277226','2022-01-01','open','Assets:Savings:Web:AliPay5','CNY','三方支付(支付宝)','assets',1),(7,'2023-10-24 11:36:12.962164','2023-10-24 11:36:12.962436','2022-01-01','open','Assets:Savings:Web:AliPay6','CNY','三方支付(支付宝)','assets',1),(8,'2023-10-24 11:37:00.972792','2023-10-24 11:37:00.972896','2022-01-01','open','Assets:Savings:Web:AliPay7','CNY','三方支付(支付宝)','assets',1),(9,'2023-10-24 11:37:07.215007','2023-10-24 11:37:07.215094','2022-01-01','open','Assets:Savings:Web:AliPay8','CNY','三方支付(支付宝)','assets',1),(10,'2023-10-24 11:38:03.184799','2023-10-24 11:38:03.184971','2022-01-01','open','Assets:Savings:Web:AliPay+','CNY','三方支付(支付宝)','assets',1);
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
  `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
INSERT INTO `auth_group` VALUES (1,'管理员组');
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
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
INSERT INTO `auth_group_permissions` VALUES (1,1,1),(2,1,2),(3,1,3),(4,1,4),(5,1,21),(6,1,22),(7,1,23),(8,1,24),(9,1,25),(10,1,26),(11,1,27),(12,1,28),(13,1,33),(14,1,34),(15,1,35),(16,1,36),(17,1,37),(18,1,38),(19,1,39),(20,1,40);
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
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add content type',4,'add_contenttype'),(14,'Can change content type',4,'change_contenttype'),(15,'Can delete content type',4,'delete_contenttype'),(16,'Can view content type',4,'view_contenttype'),(17,'Can add session',5,'add_session'),(18,'Can change session',5,'change_session'),(19,'Can delete session',5,'delete_session'),(20,'Can view session',5,'view_session'),(21,'Can add 收入映射',6,'add_assets'),(22,'Can change 收入映射',6,'change_assets'),(23,'Can delete 收入映射',6,'delete_assets'),(24,'Can view 收入映射',6,'view_assets'),(25,'Can add 支出映射',7,'add_expense'),(26,'Can change 支出映射',7,'change_expense'),(27,'Can delete 支出映射',7,'delete_expense'),(28,'Can view 支出映射',7,'view_expense'),(29,'Can add 用户',8,'add_user'),(30,'Can change 用户',8,'change_user'),(31,'Can delete 用户',8,'delete_user'),(32,'Can view 用户',8,'view_user'),(33,'Can add assets_ map',9,'add_assets_map'),(34,'Can change assets_ map',9,'change_assets_map'),(35,'Can delete assets_ map',9,'delete_assets_map'),(36,'Can view assets_ map',9,'view_assets_map'),(37,'Can add 支出映射',10,'add_expense_map'),(38,'Can change 支出映射',10,'change_expense_map'),(39,'Can delete 支出映射',10,'delete_expense_map'),(40,'Can view 支出映射',10,'view_expense_map'),(41,'Can add 资产账户',11,'add_account'),(42,'Can change 资产账户',11,'change_account'),(43,'Can delete 资产账户',11,'delete_account'),(44,'Can view 资产账户',11,'view_account'),(45,'Can add 收入映射',12,'add_income'),(46,'Can change 收入映射',12,'change_income'),(47,'Can delete 收入映射',12,'delete_income'),(48,'Can view 收入映射',12,'view_income');
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
  `password` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `first_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `last_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `mobile` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `mobile` (`mobile`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
INSERT INTO `auth_user` VALUES (1,'pbkdf2_sha256$600000$MP1gVl8Bsu3lSeMKhFrYZM$loBNe2clKKDhHrL8M1oTB0RDMasT7dAPITczbYw1QYg=','2023-12-09 11:43:35.307712',1,'test','trans','beancount','Dai_Haorui@163.com',1,1,'2023-07-30 17:22:00.000000','1234567890'),(2,'pbkdf2_sha256$600000$AqWvxpxl3mT5M2MBIgXmjN$4rNUfm8Mbs6fOpyfkearOMtU0ZVIi1bYnkIlRGHQNqM=','2023-12-09 11:42:00.000000',1,'test1','','','',1,1,'2023-07-31 12:13:00.000000','0123456789');
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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
INSERT INTO `auth_user_groups` VALUES (1,2,1);
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
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
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
  `object_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `object_repr` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
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
  `app_label` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (11,'account','account'),(1,'admin','logentry'),(3,'auth','group'),(2,'auth','permission'),(4,'contenttypes','contenttype'),(5,'sessions','session'),(6,'translate','assets'),(9,'translate','assets_map'),(7,'translate','expense'),(10,'translate','expense_map'),(12,'translate','income'),(8,'users','user');
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
  `app` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2023-07-31 14:19:23.060425'),(2,'contenttypes','0002_remove_content_type_name','2023-07-31 14:19:25.162390'),(3,'auth','0001_initial','2023-07-31 14:19:32.551226'),(4,'auth','0002_alter_permission_name_max_length','2023-07-31 14:19:34.183593'),(5,'auth','0003_alter_user_email_max_length','2023-07-31 14:19:34.304964'),(6,'auth','0004_alter_user_username_opts','2023-07-31 14:19:34.395430'),(7,'auth','0005_alter_user_last_login_null','2023-07-31 14:19:34.527187'),(8,'auth','0006_require_contenttypes_0002','2023-07-31 14:19:34.649525'),(9,'auth','0007_alter_validators_add_error_messages','2023-07-31 14:19:34.778847'),(10,'auth','0008_alter_user_username_max_length','2023-07-31 14:19:34.923386'),(11,'auth','0009_alter_user_last_name_max_length','2023-07-31 14:19:35.063294'),(12,'auth','0010_alter_group_name_max_length','2023-07-31 14:19:35.361978'),(13,'auth','0011_update_proxy_permissions','2023-07-31 14:19:35.524362'),(14,'auth','0012_alter_user_first_name_max_length','2023-07-31 14:19:35.622635'),(15,'users','0001_initial','2023-07-31 14:19:44.544314'),(16,'admin','0001_initial','2023-07-31 14:19:48.413978'),(17,'admin','0002_logentry_remove_auto_add','2023-07-31 14:19:48.542222'),(18,'admin','0003_logentry_add_action_flag_choices','2023-07-31 14:19:48.684571'),(19,'sessions','0001_initial','2023-07-31 14:19:49.712268'),(20,'translate','0001_initial','2023-07-31 14:19:50.974120'),(21,'translate','0002_initial','2023-07-31 14:19:54.103840'),(22,'translate','0003_remove_expense_payee_order','2023-09-18 15:57:47.516007'),(24,'account','0001_initial','2023-10-22 09:55:05.498335'),(25,'account','0002_alter_account_options_alter_account_account_type_and_more','2023-11-29 16:19:16.756943'),(26,'translate','0004_alter_assets_options_remove_assets_income_and_more','2023-11-30 17:02:55.908783'),(27,'translate','0005_remove_expense_classification_remove_expense_tag','2023-12-02 08:15:36.656461');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `session_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
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
INSERT INTO `django_session` VALUES ('9goyma8lct94ynof0c18qd6pq2pehj52','.eJxVjE0OwiAYRO_C2pAiNIBL956B8P1J1UBS2pXx7rZJF5rZzXszb5XyupS0dp7TROqijDr9dpDxyXUH9Mj13jS2uswT6F3RB-361ohf18P9Oyi5l23NziJH4xl9jtFaHEEcBAxndIJDYONBCIAjyRCdZ8dCHMTaMNot6vMFDsQ45A:1qgLEo:qSejg4WfDnaIz5SSPmE9xOqDch47dLQ8fxfO3saXY_Y','2023-09-27 16:28:42.744115');
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
  `key` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `full` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `owner_id` bigint NOT NULL,
  `assets` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `maps_assets_owner_id_c6403b26_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `maps_assets_owner_id_c6403b26_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=58 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_assets`
--

LOCK TABLES `maps_assets` WRITE;
/*!40000 ALTER TABLE `maps_assets` DISABLE KEYS */;
INSERT INTO `maps_assets` VALUES (1,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','5522','中国建设银行储蓄卡(5522)',1,'Assets:Savings:Bank:CCB:C5522'),(2,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','6428','中信银行信用卡(6428)',1,'Liabilities:CreditCard:Bank:CITIC:C6428'),(3,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','零钱通','微信零钱通',1,'Assets:Savings:Web:WechatFund'),(4,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','零钱','微信零钱',1,'Assets:Savings:Web:WechatPay'),(5,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','/','微信零钱',1,'Assets:Savings:Web:WechatPay'),(6,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','8837','中国招商银行储蓄卡(8837)',1,'Assets:Savings:Bank:CMB:C8837'),(7,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','1746','宁波银行储蓄卡(1746)',1,'Assets:Savings:Bank:NBCB:C1746'),(8,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','8273','中国农业银行储蓄卡(8273)',1,'Assets:Savings:Bank:ABC:C8273'),(9,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','7651','中国工商银行储蓄卡(7651)',1,'Assets:Savings:Bank:ICBC:C7651'),(10,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','5244','中国工商银行储蓄卡(5244)',1,'Assets:Savings:Bank:ICBC:C5244'),(11,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','5636','华夏银行储蓄卡(5636)',1,'Assets:Savings:Bank:HXB:C5636'),(12,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','余额','支付宝余额',1,'Assets:Savings:Web:AliPay'),(13,'2023-07-30 16:36:55.853412','2023-07-30 16:36:55.853624','余额宝','支付宝余额宝',1,'Assets:Savings:Web:AliFund'),(17,'2023-09-03 16:07:07.803743','2023-09-03 16:07:07.803774','账户余额','支付宝余额',1,'Assets:Savings:Web:AliPay'),(18,'2023-09-03 19:19:36.095363','2023-09-15 09:51:46.271442','0000','华夏银行信用卡(0000)',1,'Liabilities:CreditCard:Bank:HXB:C0000'),(19,'2023-10-13 16:39:20.651407','2023-10-13 16:39:20.651549','花呗','支付宝花呗',1,'Liabilities:CreditCard:Web:HuaBei'),(57,'2023-11-05 09:12:32.071735','2023-11-05 09:12:32.071838','5522','中国建设银行储蓄卡(5522)',2,'Assets:Savings:Bank:CCB:C5522');
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
  `key` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `payee` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `expend` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `owner_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `maps_expense_owner_id_d327d8f9_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `maps_expense_owner_id_d327d8f9_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=746 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_expense`
--

LOCK TABLES `maps_expense` WRITE;
/*!40000 ALTER TABLE `maps_expense` DISABLE KEYS */;
INSERT INTO `maps_expense` VALUES (551,'2023-11-05 09:13:40.380607','2023-11-05 09:13:40.380640','蜜雪冰城','蜜雪冰城','Expenses:Food:DrinkFruit',2),(647,'2023-12-02 08:23:35.917903','2023-12-02 08:23:56.380877','蜜雪冰城','蜜雪冰城','Expenses:Food:DrinkFruit',1),(648,'2023-12-02 08:23:36.075107','2023-12-02 08:23:36.075209','停车','','Expenses:TransPort:Private:Park',1),(649,'2023-12-02 08:23:36.196600','2023-12-02 08:23:36.196683','浙C','','Expenses:TransPort:Private:Park',1),(650,'2023-12-02 08:23:36.304126','2023-12-02 08:23:36.304160','鲜花','','Expenses:Culture',1),(651,'2023-12-02 08:23:36.412433','2023-12-02 08:23:36.412465','古茗','古茗','Expenses:Food:DrinkFruit',1),(652,'2023-12-02 08:23:36.513188','2023-12-02 08:23:36.513271','益味坊','益味坊','Expenses:Food:Breakfast',1),(653,'2023-12-02 08:23:36.902677','2023-12-02 08:23:36.902769','塔斯汀','塔斯汀','Expenses:Food',1),(654,'2023-12-02 08:23:37.077973','2023-12-02 08:23:37.078142','十足','十足','Expenses:Food',1),(655,'2023-12-02 08:23:37.153182','2023-12-02 08:23:37.153270','一点点','一点点','Expenses:Food:DrinkFruit',1),(656,'2023-12-02 08:23:37.236931','2023-12-02 08:23:37.237029','luckin','瑞幸','Expenses:Food:DrinkFruit',1),(657,'2023-12-02 08:23:37.328578','2023-12-02 08:40:33.284475','娘娘大人','娘娘大人','Expenses:Food',1),(658,'2023-12-02 08:23:37.429595','2023-12-02 08:40:51.546915','老婆大人','老婆大人','Assets:Savings:Recharge:LaoPoDaRen',1),(659,'2023-12-02 08:23:37.545957','2023-12-02 08:23:37.546042','茶百道','茶百道','Expenses:Food:DrinkFruit',1),(660,'2023-12-02 08:23:37.646098','2023-12-02 08:23:37.646190','京东','京东','Expenses:Shopping',1),(661,'2023-12-02 08:23:37.746378','2023-12-02 08:23:37.746470','包月','','Expenses:Culture:Subscription',1),(662,'2023-12-02 08:23:37.847639','2023-12-02 08:23:37.847731','正新鸡排','正新鸡排','Expenses:Food',1),(663,'2023-12-02 08:23:37.939695','2023-12-02 08:23:37.939785','奇虎智能','360','Expenses:Shopping:Digital',1),(664,'2023-12-02 08:23:38.039845','2023-12-02 08:23:38.039935','Petal On','华为','Expenses:Culture:Subscription',1),(665,'2023-12-02 08:23:38.130266','2023-12-02 08:23:38.130355','药房','','Expenses:Health:Medical',1),(666,'2023-12-02 08:23:38.240317','2023-12-02 08:23:38.240411','药店','','Expenses:Health:Medical',1),(667,'2023-12-02 08:23:38.321882','2023-12-02 08:23:38.321976','医院','','Expenses:Health',1),(668,'2023-12-02 08:23:38.421810','2023-12-02 08:23:38.421903','餐饮','','Expenses:Food',1),(669,'2023-12-02 08:23:38.530152','2023-12-02 08:23:38.530243','食品','','Expenses:Food',1),(670,'2023-12-02 08:23:38.650092','2023-12-02 08:23:38.650183','深圳市腾讯天游科技有限公司','','Expenses:Culture:Entertainment',1),(671,'2023-12-02 08:23:38.733683','2023-12-02 08:23:38.733776','水果','','Expenses:Food:DrinkFruit',1),(672,'2023-12-02 08:23:38.821955','2023-12-02 08:23:38.822088','早餐','','Expenses:Food:Breakfast',1),(673,'2023-12-02 08:23:38.930182','2023-12-02 08:23:38.930272','充电','','Expenses:TransPort:Private:Fuel',1),(674,'2023-12-02 08:23:39.034630','2023-12-02 08:23:39.034719','加油','','Expenses:TransPort:Private:Fuel',1),(675,'2023-12-02 08:23:39.121886','2023-12-02 08:23:39.121977','瑞安市供电局','国家电网','Expenses:Home:Recharge',1),(676,'2023-12-02 08:23:39.221874','2023-12-02 08:23:39.221969','ETC','','Expenses:TransPort:Public',1),(677,'2023-12-02 08:23:39.322318','2023-12-02 08:23:39.322417','华为终端有限公司','华为','Expenses:Shopping:Digital',1),(678,'2023-12-02 08:23:39.422056','2023-12-02 08:23:39.422145','饿了么','饿了么','Expenses:Food',1),(679,'2023-12-02 08:23:39.561871','2023-12-02 08:23:39.561964','美团','美团','Expenses:Food',1),(680,'2023-12-02 08:23:39.654062','2023-12-02 08:23:39.654155','地铁','','Expenses:TransPort:Public',1),(681,'2023-12-02 08:23:39.745916','2023-12-02 08:23:39.746011','国网智慧车联网','国家电网','Expenses:TransPort:Private:Fuel',1),(682,'2023-12-02 08:23:39.846153','2023-12-02 08:23:39.846242','肯德基','肯德基','Expenses:Food',1),(683,'2023-12-02 08:23:39.938149','2023-12-02 08:23:39.938238','华为','华为','Expenses:Shopping',1),(684,'2023-12-02 08:23:40.063358','2023-12-02 08:23:40.063450','沙县小吃','沙县小吃','Expenses:Food',1),(685,'2023-12-02 08:23:40.155229','2023-12-02 08:23:40.155317','一鸣','一鸣','Expenses:Food',1),(686,'2023-12-02 08:23:40.247136','2023-12-02 08:23:40.247226','之上','之上','Expenses:Food',1),(687,'2023-12-02 08:23:40.347403','2023-12-02 08:23:40.347501','大疆','','Expenses:Shopping:Digital',1),(688,'2023-12-02 08:23:40.456593','2023-12-02 08:23:40.456701','12306','12306','Expenses:TransPort:Public',1),(689,'2023-12-02 08:23:40.540134','2023-12-02 08:23:40.540171','阿里云','阿里云','Expenses:Culture:Subscription',1),(690,'2023-12-02 08:23:40.629342','2023-12-02 08:23:40.629390','电影','','Expenses:Culture:Entertainment',1),(691,'2023-12-02 08:23:40.729204','2023-12-02 08:23:40.729236','火车票','','Expenses:TransPort:Public',1),(692,'2023-12-02 08:23:40.832379','2023-12-02 08:23:40.832412','高铁','','Expenses:TransPort:Public',1),(693,'2023-12-02 08:23:40.913704','2023-12-02 08:23:40.913798','机票','','Expenses:TransPort:Public',1),(694,'2023-12-02 08:23:41.021968','2023-12-02 08:23:41.022084','医疗','','Expenses:Health',1),(695,'2023-12-02 08:23:41.130336','2023-12-02 08:23:41.130427','医生','','Expenses:Health',1),(696,'2023-12-02 08:23:41.267735','2023-12-02 08:23:41.267830','医用','','Expenses:Health',1),(697,'2023-12-02 08:23:41.386093','2023-12-02 08:23:41.386186','小吃','','Expenses:Food',1),(698,'2023-12-02 08:23:41.562783','2023-12-02 08:23:41.562892','餐厅','','Expenses:Food',1),(699,'2023-12-02 08:23:41.670824','2023-12-02 08:23:41.670914','小食','','Expenses:Food',1),(700,'2023-12-02 08:23:41.788174','2023-12-02 08:23:41.788269','旗舰店','淘宝','Expenses:Shopping',1),(701,'2023-12-02 08:23:41.921105','2023-12-02 08:41:24.020565','粮粮驾到','粮粮驾到','Assets:Savings:Recharge:LiangLiangJiaDao',1),(702,'2023-12-02 08:23:42.037638','2023-12-02 08:23:42.037668','中国石油','中国石油','Expenses:TransPort:Private:Fuel',1),(703,'2023-12-02 08:23:42.137948','2023-12-02 08:23:42.137997','酒店','','Expenses:Culture',1),(705,'2023-12-02 08:23:42.338192','2023-12-02 08:23:42.338238','高德','高德','Expenses:TransPort:Public',1),(706,'2023-12-02 08:23:42.447073','2023-12-02 08:23:42.447104','烟酒','','Expenses:Food:DrinkFruit',1),(707,'2023-12-02 08:23:42.537721','2023-12-02 08:23:42.537753','理发','','Expenses:Shopping:Makeup',1),(708,'2023-12-02 08:23:42.647678','2023-12-02 08:23:42.647708','美发','','Expenses:Shopping:Makeup',1),(709,'2023-12-02 08:23:42.737851','2023-12-02 08:23:42.737881','美容','','Expenses:Shopping:Makeup',1),(710,'2023-12-02 08:23:42.841309','2023-12-02 08:23:42.841358','华莱士','华莱士','Expenses:Food',1),(711,'2023-12-02 08:23:43.142080','2023-12-02 08:23:43.142116','晚餐','','Expenses:Food:Dinner',1),(712,'2023-12-02 08:23:43.435311','2023-12-02 08:23:43.435418','午餐','','Expenses:Food:Lunch',1),(713,'2023-12-02 08:23:43.547162','2023-12-02 08:23:43.547263','新时沏','新时沏','Expenses:Food:DrinkFruit',1),(714,'2023-12-02 08:23:43.678591','2023-12-02 08:23:43.678747','得物','得物','Expenses:Shopping',1),(715,'2023-12-02 08:23:43.803118','2023-12-02 08:23:43.803217','拼多多','拼多多','Expenses:Shopping',1),(716,'2023-12-02 08:23:43.887491','2023-12-04 16:17:46.165287','移动','中国移动','Assets:Savings:Recharge:Operator:Mobile:C6428',1),(717,'2023-12-02 08:23:44.061428','2023-12-06 09:55:32.818372','电信','中国电信','Assets:Savings:Recharge:Operator:Telecom:C6428',1),(718,'2023-12-02 08:23:44.221394','2023-12-06 09:56:20.759395','联通','中国联通','Assets:Savings:Recharge:Operator:Unicom:C6428',1),(719,'2023-12-02 08:23:44.397218','2023-12-02 08:23:44.397246','深圳市腾讯计算机系统有限公司','','Expenses:Culture',1),(720,'2023-12-02 08:23:44.472430','2023-12-02 08:23:44.472460','胖哥俩','胖哥俩','Expenses:Food',1),(721,'2023-12-02 08:23:44.582032','2023-12-02 08:23:44.582120','服装','','Expenses:Shopping:Clothing',1),(722,'2023-12-02 08:23:44.674059','2023-12-02 08:23:44.674150','衣服','','Expenses:Shopping:Clothing',1),(723,'2023-12-02 08:23:44.774347','2023-12-02 08:23:44.774550','裤子','','Expenses:Shopping:Clothing',1),(724,'2023-12-02 08:23:44.866581','2023-12-02 08:23:44.866671','鞋子','','Expenses:Shopping:Clothing',1),(725,'2023-12-02 08:23:44.947175','2023-12-02 08:23:44.947265','袜子','','Expenses:Shopping:Clothing',1),(726,'2023-12-02 08:23:45.047351','2023-12-02 08:23:45.047436','华为软件技术有限公司','华为','Expenses:Culture:Subscription',1),(727,'2023-12-02 08:23:45.155645','2023-12-02 08:23:45.155738','淘宝','淘宝','Expenses:Shopping',1),(728,'2023-12-02 08:23:45.268624','2023-12-02 08:23:45.268738','医保','','Expenses:Health',1),(729,'2023-12-02 08:23:45.368856','2023-12-02 08:23:45.368947','自动续费','','Expenses:Culture:Subscription',1),(730,'2023-12-02 08:23:45.485793','2023-12-02 08:23:45.485884','诊疗','','Expenses:Health',1),(731,'2023-12-02 08:23:45.594605','2023-12-02 08:23:45.594698','卫生','','Expenses:Health',1),(732,'2023-12-02 08:23:45.678192','2023-12-02 08:23:45.678282','统一公共支付平台','','Expenses:Government',1),(733,'2023-12-02 08:23:45.778454','2023-12-02 08:23:45.778546','彩票','','Expenses:Culture',1),(734,'2023-12-02 08:23:45.861983','2023-12-02 08:23:45.862232','超市','','Expenses:Shopping',1),(735,'2023-12-02 08:23:45.989149','2023-12-02 08:23:45.989242','大润发','','Expenses:Shopping',1),(736,'2023-12-02 08:23:46.095913','2023-12-02 08:23:46.095996','便利店','','Expenses:Shopping',1),(737,'2023-12-02 08:23:46.221312','2023-12-02 08:23:46.221400','兰州拉面','兰州拉面','Expenses:Food',1),(738,'2023-12-02 08:23:46.304812','2023-12-02 08:23:46.304904','供水','国家水网','Expenses:Home:Recharge',1),(739,'2023-12-02 08:49:19.376113','2023-12-02 08:49:19.376213','绝味鸭脖','绝味鸭脖','Expenses:Food',1),(740,'2023-12-02 08:53:21.135458','2023-12-02 08:53:21.135564','舒活食品','一鸣','Assets:Savings:Recharge:YiMin',1),(741,'2023-12-04 15:10:16.484723','2023-12-04 15:10:16.484765','抖音生活服务','抖音','Expenses:Food',1),(742,'2023-12-04 15:12:20.302240','2023-12-04 15:12:20.302277','医药','','Expenses:Health',1),(743,'2023-12-04 15:41:05.187768','2023-12-04 15:41:31.084752','饮料','','Expenses:Food:DrinkFruit',1),(744,'2023-12-05 09:42:56.952854','2023-12-05 09:42:56.952893','抖音月付','抖音','Liabilities:CreditCard:Web:DouYin',1),(745,'2023-12-06 10:20:58.331837','2023-12-06 10:20:58.331876','公益','','Expenses:Culture',1);
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
  `key` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `payer` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `income` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `owner_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `maps_income_owner_id_72c1c0ab_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `maps_income_owner_id_72c1c0ab_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_income`
--

LOCK TABLES `maps_income` WRITE;
/*!40000 ALTER TABLE `maps_income` DISABLE KEYS */;
INSERT INTO `maps_income` VALUES (1,'2023-12-01 16:29:20.420133','2023-12-01 16:29:20.420181','红包',NULL,'Income:Receivables:RedPacket',1),(4,'2023-12-02 08:54:01.990404','2023-12-02 08:54:01.990502','老婆',NULL,'Liabilities:Payables:Personal',1);
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

-- Dump completed on 2023-12-09 11:47:25

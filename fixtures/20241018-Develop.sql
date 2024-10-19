-- MySQL dump 10.13  Distrib 9.0.1, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: beancount-trans
-- ------------------------------------------------------
-- Server version	9.0.1

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
-- Table structure for table `account_emailaddress`
--

DROP TABLE IF EXISTS `account_emailaddress`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `account_emailaddress` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(254) NOT NULL,
  `verified` tinyint(1) NOT NULL,
  `primary` tinyint(1) NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `account_emailaddress_user_id_email_987c8728_uniq` (`user_id`,`email`),
  KEY `account_emailaddress_email_03be32b2` (`email`),
  CONSTRAINT `account_emailaddress_user_id_2c513194_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `account_emailaddress`
--

LOCK TABLES `account_emailaddress` WRITE;
/*!40000 ALTER TABLE `account_emailaddress` DISABLE KEYS */;
/*!40000 ALTER TABLE `account_emailaddress` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `account_emailconfirmation`
--

DROP TABLE IF EXISTS `account_emailconfirmation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `account_emailconfirmation` (
  `id` int NOT NULL AUTO_INCREMENT,
  `created` datetime(6) NOT NULL,
  `sent` datetime(6) DEFAULT NULL,
  `key` varchar(64) NOT NULL,
  `email_address_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`),
  KEY `account_emailconfirm_email_address_id_5b7f8c58_fk_account_e` (`email_address_id`),
  CONSTRAINT `account_emailconfirm_email_address_id_5b7f8c58_fk_account_e` FOREIGN KEY (`email_address_id`) REFERENCES `account_emailaddress` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `account_emailconfirmation`
--

LOCK TABLES `account_emailconfirmation` WRITE;
/*!40000 ALTER TABLE `account_emailconfirmation` DISABLE KEYS */;
/*!40000 ALTER TABLE `account_emailconfirmation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
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
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add user',4,'add_user'),(14,'Can change user',4,'change_user'),(15,'Can delete user',4,'delete_user'),(16,'Can view user',4,'view_user'),(17,'Can add content type',5,'add_contenttype'),(18,'Can change content type',5,'change_contenttype'),(19,'Can delete content type',5,'delete_contenttype'),(20,'Can view content type',5,'view_contenttype'),(21,'Can add session',6,'add_session'),(22,'Can change session',6,'change_session'),(23,'Can delete session',6,'delete_session'),(24,'Can view session',6,'view_session'),(25,'Can add site',7,'add_site'),(26,'Can change site',7,'change_site'),(27,'Can delete site',7,'delete_site'),(28,'Can view site',7,'view_site'),(29,'Can add 资产映射',8,'add_assets'),(30,'Can change 资产映射',8,'change_assets'),(31,'Can delete 资产映射',8,'delete_assets'),(32,'Can view 资产映射',8,'view_assets'),(33,'Can add 支出映射',9,'add_expense'),(34,'Can change 支出映射',9,'change_expense'),(35,'Can delete 支出映射',9,'delete_expense'),(36,'Can view 支出映射',9,'view_expense'),(37,'Can add 收入映射',10,'add_income'),(38,'Can change 收入映射',10,'change_income'),(39,'Can delete 收入映射',10,'delete_income'),(40,'Can view 收入映射',10,'view_income'),(41,'Can add OwnTrackLogs',11,'add_owntracklog'),(42,'Can change OwnTrackLogs',11,'change_owntracklog'),(43,'Can delete OwnTrackLogs',11,'delete_owntracklog'),(44,'Can view OwnTrackLogs',11,'view_owntracklog'),(45,'Can add Token',12,'add_token'),(46,'Can change Token',12,'change_token'),(47,'Can delete Token',12,'delete_token'),(48,'Can view Token',12,'view_token'),(49,'Can add Token',13,'add_tokenproxy'),(50,'Can change Token',13,'change_tokenproxy'),(51,'Can delete Token',13,'delete_tokenproxy'),(52,'Can view Token',13,'view_tokenproxy'),(53,'Can add email address',14,'add_emailaddress'),(54,'Can change email address',14,'change_emailaddress'),(55,'Can delete email address',14,'delete_emailaddress'),(56,'Can view email address',14,'view_emailaddress'),(57,'Can add email confirmation',15,'add_emailconfirmation'),(58,'Can change email confirmation',15,'change_emailconfirmation'),(59,'Can delete email confirmation',15,'delete_emailconfirmation'),(60,'Can view email confirmation',15,'view_emailconfirmation'),(61,'Can add social account',16,'add_socialaccount'),(62,'Can change social account',16,'change_socialaccount'),(63,'Can delete social account',16,'delete_socialaccount'),(64,'Can view social account',16,'view_socialaccount'),(65,'Can add social application',17,'add_socialapp'),(66,'Can change social application',17,'change_socialapp'),(67,'Can delete social application',17,'delete_socialapp'),(68,'Can view social application',17,'view_socialapp'),(69,'Can add social application token',18,'add_socialtoken'),(70,'Can change social application token',18,'change_socialtoken'),(71,'Can delete social application token',18,'delete_socialtoken'),(72,'Can view social application token',18,'view_socialtoken'),(73,'Can add authenticator',19,'add_authenticator'),(74,'Can change authenticator',19,'change_authenticator'),(75,'Can delete authenticator',19,'delete_authenticator'),(76,'Can view authenticator',19,'view_authenticator'),(77,'Can add user session',20,'add_usersession'),(78,'Can change user session',20,'change_usersession'),(79,'Can delete user session',20,'delete_usersession'),(80,'Can view user session',20,'view_usersession');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
INSERT INTO `auth_user` VALUES (1,'pbkdf2_sha256$870000$apU8iaYc3AOfcfp5sVHWs2$RXz+pPWJLMo8MSDf7z9FzuePx5VCIn0UarifKVfnpS0=',NULL,1,'admin','','','',1,1,'2024-10-18 16:57:23.830349');
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
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
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
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `authtoken_token`
--

DROP TABLE IF EXISTS `authtoken_token`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `authtoken_token` (
  `key` varchar(40) NOT NULL,
  `created` datetime(6) NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`key`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `authtoken_token_user_id_35299eff_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `authtoken_token`
--

LOCK TABLES `authtoken_token` WRITE;
/*!40000 ALTER TABLE `authtoken_token` DISABLE KEYS */;
/*!40000 ALTER TABLE `authtoken_token` ENABLE KEYS */;
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
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=392 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
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
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (14,'account','emailaddress'),(15,'account','emailconfirmation'),(1,'admin','logentry'),(3,'auth','group'),(2,'auth','permission'),(4,'auth','user'),(12,'authtoken','token'),(13,'authtoken','tokenproxy'),(5,'contenttypes','contenttype'),(19,'mfa','authenticator'),(11,'owntracks','owntracklog'),(6,'sessions','session'),(7,'sites','site'),(16,'socialaccount','socialaccount'),(17,'socialaccount','socialapp'),(18,'socialaccount','socialtoken'),(8,'translate','assets'),(9,'translate','expense'),(10,'translate','income'),(20,'usersessions','usersession');
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
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2024-08-19 10:48:23.494773'),(2,'auth','0001_initial','2024-08-19 10:48:24.905580'),(3,'account','0001_initial','2024-08-19 10:48:25.338005'),(4,'account','0002_email_max_length','2024-08-19 10:48:25.388661'),(5,'account','0003_alter_emailaddress_create_unique_verified_email','2024-08-19 10:48:25.461165'),(6,'account','0004_alter_emailaddress_drop_unique_email','2024-08-19 10:48:25.529448'),(7,'account','0005_emailaddress_idx_upper_email','2024-08-19 10:48:25.596997'),(8,'account','0006_emailaddress_lower','2024-08-19 10:48:25.618701'),(9,'account','0007_emailaddress_idx_email','2024-08-19 10:48:25.713225'),(10,'account','0008_emailaddress_unique_primary_email_fixup','2024-08-19 10:48:25.735933'),(11,'account','0009_emailaddress_unique_primary_email','2024-08-19 10:48:25.747987'),(12,'admin','0001_initial','2024-08-19 10:48:26.088749'),(13,'admin','0002_logentry_remove_auto_add','2024-08-19 10:48:26.113781'),(14,'admin','0003_logentry_add_action_flag_choices','2024-08-19 10:48:26.131711'),(15,'contenttypes','0002_remove_content_type_name','2024-08-19 10:48:26.309046'),(16,'auth','0002_alter_permission_name_max_length','2024-08-19 10:48:26.466237'),(17,'auth','0003_alter_user_email_max_length','2024-08-19 10:48:26.510478'),(18,'auth','0004_alter_user_username_opts','2024-08-19 10:48:26.530687'),(19,'auth','0005_alter_user_last_login_null','2024-08-19 10:48:26.645568'),(20,'auth','0006_require_contenttypes_0002','2024-08-19 10:48:26.653464'),(21,'auth','0007_alter_validators_add_error_messages','2024-08-19 10:48:26.677165'),(22,'auth','0008_alter_user_username_max_length','2024-08-19 10:48:26.836660'),(23,'auth','0009_alter_user_last_name_max_length','2024-08-19 10:48:27.003106'),(24,'auth','0010_alter_group_name_max_length','2024-08-19 10:48:27.048853'),(25,'auth','0011_update_proxy_permissions','2024-08-19 10:48:27.075809'),(26,'auth','0012_alter_user_first_name_max_length','2024-08-19 10:48:27.211707'),(27,'authtoken','0001_initial','2024-08-19 10:48:27.404676'),(28,'authtoken','0002_auto_20160226_1747','2024-08-19 10:48:27.445458'),(29,'authtoken','0003_tokenproxy','2024-08-19 10:48:27.452325'),(30,'authtoken','0004_alter_tokenproxy_options','2024-08-19 10:48:27.460365'),(31,'owntracks','0001_initial','2024-08-19 10:48:27.509401'),(32,'sessions','0001_initial','2024-08-19 10:48:27.642823'),(33,'sites','0001_initial','2024-08-19 10:48:27.697451'),(34,'sites','0002_alter_domain_unique','2024-08-19 10:48:27.746874'),(35,'socialaccount','0001_initial','2024-08-19 10:48:28.812385'),(36,'socialaccount','0002_token_max_lengths','2024-08-19 10:48:28.889344'),(37,'socialaccount','0003_extra_data_default_dict','2024-08-19 10:48:28.909390'),(38,'socialaccount','0004_app_provider_id_settings','2024-08-19 10:48:29.302698'),(39,'socialaccount','0005_socialtoken_nullable_app','2024-08-19 10:48:29.683709'),(40,'socialaccount','0006_alter_socialaccount_extra_data','2024-08-19 10:48:29.858931'),(41,'translate','0001_initial','2024-08-19 10:48:29.958876'),(42,'translate','0002_initial','2024-08-19 10:48:30.262438'),(43,'translate','0003_remove_expense_payee_order','2024-08-19 10:48:30.319685'),(44,'translate','0004_alter_assets_options_remove_assets_income_and_more','2024-08-19 10:48:30.635143'),(45,'translate','0005_remove_expense_classification_remove_expense_tag','2024-08-19 10:48:30.725645'),(46,'mfa','0001_initial','2024-08-27 10:14:33.611005'),(47,'mfa','0002_authenticator_timestamps','2024-08-27 10:14:33.718122'),(48,'usersessions','0001_initial','2024-08-27 10:14:33.944340'),(49,'mfa','0003_authenticator_type_uniq','2024-08-28 17:04:55.383835');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_site`
--

DROP TABLE IF EXISTS `django_site`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_site` (
  `id` int NOT NULL AUTO_INCREMENT,
  `domain` varchar(100) NOT NULL,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_site_domain_a2e37b91_uniq` (`domain`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_site`
--

LOCK TABLES `django_site` WRITE;
/*!40000 ALTER TABLE `django_site` DISABLE KEYS */;
INSERT INTO `django_site` VALUES (1,'example.com','example.com'),(2,'127.0.0.1','127.0.0.1'),(3,'http://127.0.0.1:8002/','http://127.0.0.1:8002/'),(4,'http://localhost:5173/','http://localhost:5173/');
/*!40000 ALTER TABLE `django_site` ENABLE KEYS */;
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
  `key` varchar(16) NOT NULL,
  `full` varchar(16) NOT NULL,
  `owner_id` int NOT NULL,
  `assets` varchar(64) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `maps_assets_owner_id_c6403b26_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `maps_assets_owner_id_c6403b26_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=177 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_assets`
--

LOCK TABLES `maps_assets` WRITE;
/*!40000 ALTER TABLE `maps_assets` DISABLE KEYS */;
INSERT INTO `maps_assets` VALUES (155,'2024-10-18 16:58:16.416702','2024-10-18 16:58:16.416811','5522','中国建设银行储蓄卡(5522)',1,'Assets:Savings:Bank:CCB:C5522'),(156,'2024-10-18 16:58:16.424300','2024-10-18 16:58:16.424363','6428','中信银行信用卡(6428)',1,'Liabilities:CreditCard:Bank:CITIC:C6428'),(157,'2024-10-18 16:58:16.430627','2024-10-18 16:58:16.430663','零钱通','微信零钱通',1,'Assets:Savings:Web:WechatFund'),(158,'2024-10-18 16:58:16.438595','2024-10-18 16:58:16.438657','零钱','微信零钱',1,'Assets:Savings:Web:WechatPay'),(159,'2024-10-18 16:58:16.447023','2024-10-18 16:58:16.447085','/','微信零钱',1,'Assets:Savings:Web:WechatPay'),(160,'2024-10-18 16:58:16.454783','2024-10-18 16:58:16.454854','8837','中国招商银行储蓄卡(8837)',1,'Assets:Savings:Bank:CMB:C8837'),(161,'2024-10-18 16:58:16.463299','2024-10-18 16:58:16.463373','1746','宁波银行储蓄卡(1746)',1,'Assets:Savings:Bank:NBCB:C1746'),(162,'2024-10-18 16:58:16.470996','2024-10-18 16:58:16.471047','8273','中国农业银行储蓄卡(8273)',1,'Assets:Savings:Bank:ABC:C8273'),(163,'2024-10-18 16:58:16.479468','2024-10-18 16:58:16.479526','7651','中国工商银行储蓄卡(7651)',1,'Assets:Savings:Bank:ICBC:C7651'),(164,'2024-10-18 16:58:16.486894','2024-10-18 16:58:16.486942','5244','中国工商银行储蓄卡(5244)',1,'Assets:Savings:Bank:ICBC:C5244'),(165,'2024-10-18 16:58:16.493188','2024-10-18 16:58:16.493256','5636','华夏银行储蓄卡(5636)',1,'Assets:Savings:Bank:HXB:C5636'),(166,'2024-10-18 16:58:16.500986','2024-10-18 16:58:16.501048','余额宝','支付宝余额宝',1,'Assets:Savings:Web:AliFund'),(167,'2024-10-18 16:58:16.509156','2024-10-18 16:58:16.509211','余额','支付宝余额',1,'Assets:Savings:Web:AliPay'),(168,'2024-10-18 16:58:16.519497','2024-10-18 16:58:16.519545','戴某轩','小荷包(戴某轩)',1,'Assets:Savings:Web:XiaoHeBao:DaiMouXuan'),(169,'2024-10-18 16:58:16.526048','2024-10-18 16:58:16.526117','账户余额','支付宝余额',1,'Assets:Savings:Web:AliPay'),(170,'2024-10-18 16:58:16.533740','2024-10-18 16:58:16.533791','花呗','支付宝花呗',1,'Liabilities:CreditCard:Web:HuaBei'),(171,'2024-10-18 16:58:16.542468','2024-10-18 16:58:16.542529','4523','中国招商银行信用卡(4523)',1,'Liabilities:CreditCard:Bank:CMB:C4523'),(172,'2024-10-18 16:58:16.552827','2024-10-18 16:58:16.552874','8313','中国招商银行信用卡(8313)',1,'Liabilities:CreditCard:Bank:CMB:C8313'),(173,'2024-10-18 16:58:16.561069','2024-10-18 16:58:16.561171','9813','中国招商银行信用卡(9813)',1,'Liabilities:CreditCard:Bank:CMB:C9813'),(174,'2024-10-18 16:58:16.569521','2024-10-18 16:58:16.569595','0005','浙江农商银行储蓄卡(0005)',1,'Assets:Savings:Bank:ZJRCUB:C0005'),(175,'2024-10-18 16:58:16.577432','2024-10-18 16:58:16.577506','0814','中国银行储蓄卡(0814)',1,'Assets:Savings:Bank:BOC:C0814'),(176,'2024-10-18 16:58:16.585864','2024-10-18 16:58:16.585937','4144','中国光大银行储蓄卡(4144)',1,'Assets:Savings:Bank:CEB:C4144');
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
  `key` varchar(16) NOT NULL,
  `payee` varchar(8) DEFAULT NULL,
  `expend` varchar(64) NOT NULL,
  `owner_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `maps_expense_owner_id_d327d8f9_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `maps_expense_owner_id_d327d8f9_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1642 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_expense`
--

LOCK TABLES `maps_expense` WRITE;
/*!40000 ALTER TABLE `maps_expense` DISABLE KEYS */;
INSERT INTO `maps_expense` VALUES (1464,'2024-10-18 16:58:04.907992','2024-10-18 16:58:04.908038','蜜雪冰城','蜜雪冰城','Expenses:Food:DrinkFruit',1),(1465,'2024-10-18 16:58:04.914883','2024-10-18 16:58:04.914920','停车','','Expenses:TransPort:Private:Park',1),(1466,'2024-10-18 16:58:04.921583','2024-10-18 16:58:04.921628','浙C','','Expenses:TransPort:Private:Park',1),(1467,'2024-10-18 16:58:04.928755','2024-10-18 16:58:04.928813','鲜花','','Expenses:Culture',1),(1468,'2024-10-18 16:58:04.935887','2024-10-18 16:58:04.935955','古茗','古茗','Expenses:Food:DrinkFruit',1),(1469,'2024-10-18 16:58:04.943294','2024-10-18 16:58:04.943413','益味坊','益味坊','Expenses:Food:Breakfast',1),(1470,'2024-10-18 16:58:04.952703','2024-10-18 16:58:04.952766','塔斯汀','塔斯汀','Expenses:Food',1),(1471,'2024-10-18 16:58:04.959595','2024-10-18 16:58:04.959639','十足','十足','Expenses:Food',1),(1472,'2024-10-18 16:58:04.965814','2024-10-18 16:58:04.965843','一点点','一点点','Expenses:Food:DrinkFruit',1),(1473,'2024-10-18 16:58:04.972012','2024-10-18 16:58:04.972038','luckin','瑞幸','Expenses:Food:DrinkFruit',1),(1474,'2024-10-18 16:58:04.978025','2024-10-18 16:58:04.978052','娘娘大人','娘娘大人','Expenses:Food',1),(1475,'2024-10-18 16:58:04.984285','2024-10-18 16:58:04.984321','老婆大人','老婆大人','Assets:Savings:Recharge:LaoPoDaRen',1),(1476,'2024-10-18 16:58:04.990685','2024-10-18 16:58:04.990727','茶百道','茶百道','Expenses:Food:DrinkFruit',1),(1477,'2024-10-18 16:58:04.997378','2024-10-18 16:58:04.997431','京东','京东','Expenses:Shopping',1),(1478,'2024-10-18 16:58:05.005044','2024-10-18 16:58:05.005103','包月','','Expenses:Culture:Subscription',1),(1479,'2024-10-18 16:58:05.027435','2024-10-18 16:58:05.027513','正新鸡排','正新鸡排','Expenses:Food',1),(1480,'2024-10-18 16:58:05.036607','2024-10-18 16:58:05.036669','奇虎智能','360','Expenses:Shopping:Digital',1),(1481,'2024-10-18 16:58:05.043929','2024-10-18 16:58:05.043990','Petal On','华为','Expenses:Culture:Subscription',1),(1482,'2024-10-18 16:58:05.053751','2024-10-18 16:58:05.053846','药房','','Expenses:Health:Medical',1),(1483,'2024-10-18 16:58:05.069902','2024-10-18 16:58:05.069950','药店','','Expenses:Health:Medical',1),(1484,'2024-10-18 16:58:05.076264','2024-10-18 16:58:05.076294','医院','','Expenses:Health',1),(1485,'2024-10-18 16:58:05.082350','2024-10-18 16:58:05.082362','餐饮','','Expenses:Food',1),(1486,'2024-10-18 16:58:05.087961','2024-10-18 16:58:05.087973','食品','','Expenses:Food',1),(1487,'2024-10-18 16:58:05.094041','2024-10-18 16:58:05.094057','深圳市腾讯天游科技有限公司','','Expenses:Culture:Entertainment',1),(1488,'2024-10-18 16:58:05.100196','2024-10-18 16:58:05.100213','水果','','Expenses:Food:DrinkFruit',1),(1489,'2024-10-18 16:58:05.106529','2024-10-18 16:58:05.106564','早餐','','Expenses:Food:Breakfast',1),(1490,'2024-10-18 16:58:05.113929','2024-10-18 16:58:05.113984','充电','','Expenses:TransPort:Private:Fuel',1),(1491,'2024-10-18 16:58:05.123081','2024-10-18 16:58:05.123142','加油','','Expenses:TransPort:Private:Fuel',1),(1492,'2024-10-18 16:58:05.134142','2024-10-18 16:58:05.134213','供电局','国家电网','Expenses:Home:Recharge',1),(1493,'2024-10-18 16:58:05.143296','2024-10-18 16:58:05.143358','ETC','','Expenses:TransPort:Public',1),(1494,'2024-10-18 16:58:05.150015','2024-10-18 16:58:05.150065','华为终端有限公司','华为','Expenses:Shopping:Digital',1),(1495,'2024-10-18 16:58:05.156983','2024-10-18 16:58:05.157041','饿了么','饿了么','Expenses:Food',1),(1496,'2024-10-18 16:58:05.164113','2024-10-18 16:58:05.164171','美团平台商户','美团','Expenses:Food',1),(1497,'2024-10-18 16:58:05.171219','2024-10-18 16:58:05.171274','地铁','','Expenses:TransPort:Public',1),(1498,'2024-10-18 16:58:05.181741','2024-10-18 16:58:05.181802','国网智慧车联网','国家电网','Expenses:TransPort:Private:Fuel',1),(1499,'2024-10-18 16:58:05.190193','2024-10-18 16:58:05.190244','肯德基','肯德基','Expenses:Food',1),(1500,'2024-10-18 16:58:05.198605','2024-10-18 16:58:05.198681','华为','华为','Expenses:Shopping',1),(1501,'2024-10-18 16:58:05.207824','2024-10-18 16:58:05.207888','沙县小吃','沙县小吃','Expenses:Food',1),(1502,'2024-10-18 16:58:05.216248','2024-10-18 16:58:05.216308','一鸣','一鸣','Expenses:Food',1),(1503,'2024-10-18 16:58:05.224921','2024-10-18 16:58:05.224999','之上','之上','Expenses:Food',1),(1504,'2024-10-18 16:58:05.233052','2024-10-18 16:58:05.233343','大疆','','Expenses:Shopping:Digital',1),(1505,'2024-10-18 16:58:05.242213','2024-10-18 16:58:05.242274','12306','12306','Expenses:TransPort:Public',1),(1506,'2024-10-18 16:58:05.249349','2024-10-18 16:58:05.249402','阿里云','阿里云','Expenses:Culture:Subscription',1),(1507,'2024-10-18 16:58:05.256297','2024-10-18 16:58:05.256356','电影','','Expenses:Culture:Entertainment',1),(1508,'2024-10-18 16:58:05.263317','2024-10-18 16:58:05.263363','火车票','','Expenses:TransPort:Public',1),(1509,'2024-10-18 16:58:05.270287','2024-10-18 16:58:05.270332','高铁','','Expenses:TransPort:Public',1),(1510,'2024-10-18 16:58:05.277291','2024-10-18 16:58:05.277346','机票','','Expenses:TransPort:Public',1),(1511,'2024-10-18 16:58:05.284255','2024-10-18 16:58:05.284299','医疗','','Expenses:Health',1),(1512,'2024-10-18 16:58:05.291215','2024-10-18 16:58:05.291260','医生','','Expenses:Health',1),(1513,'2024-10-18 16:58:05.298280','2024-10-18 16:58:05.298339','医用','','Expenses:Health',1),(1514,'2024-10-18 16:58:05.305998','2024-10-18 16:58:05.306055','小吃','','Expenses:Food',1),(1515,'2024-10-18 16:58:05.314769','2024-10-18 16:58:05.314823','餐厅','','Expenses:Food',1),(1516,'2024-10-18 16:58:05.321605','2024-10-18 16:58:05.321648','小食','','Expenses:Food',1),(1517,'2024-10-18 16:58:05.331959','2024-10-18 16:58:05.332027','旗舰店','淘宝','Expenses:Shopping',1),(1518,'2024-10-18 16:58:05.340328','2024-10-18 16:58:05.340380','粮粮驾到','粮粮驾到','Assets:Savings:Recharge:LiangLiangJiaDao',1),(1519,'2024-10-18 16:58:05.348339','2024-10-18 16:58:05.348397','中国石油','中国石油','Expenses:TransPort:Private:Fuel',1),(1520,'2024-10-18 16:58:05.356657','2024-10-18 16:58:05.356702','酒店','','Expenses:Culture',1),(1521,'2024-10-18 16:58:05.364285','2024-10-18 16:58:05.364350','某义','老婆','Expenses:Relationship',1),(1522,'2024-10-18 16:58:05.372830','2024-10-18 16:58:05.372883','高德','高德','Expenses:TransPort:Public',1),(1523,'2024-10-18 16:58:05.379352','2024-10-18 16:58:05.379409','烟酒','','Expenses:Food:DrinkFruit',1),(1524,'2024-10-18 16:58:05.385677','2024-10-18 16:58:05.385723','理发','','Expenses:Shopping:Makeup',1),(1525,'2024-10-18 16:58:05.393280','2024-10-18 16:58:05.393332','美发','','Expenses:Shopping:Makeup',1),(1526,'2024-10-18 16:58:05.401786','2024-10-18 16:58:05.401834','美容','','Expenses:Shopping:Makeup',1),(1527,'2024-10-18 16:58:05.410333','2024-10-18 16:58:05.410397','华莱士','华莱士','Expenses:Food',1),(1528,'2024-10-18 16:58:05.418731','2024-10-18 16:58:05.418784','晚餐','','Expenses:Food:Dinner',1),(1529,'2024-10-18 16:58:05.426325','2024-10-18 16:58:05.426384','午餐','','Expenses:Food:Lunch',1),(1530,'2024-10-18 16:58:05.434961','2024-10-18 16:58:05.435011','新时沏','新时沏','Expenses:Food:DrinkFruit',1),(1531,'2024-10-18 16:58:05.441432','2024-10-18 16:58:05.441474','得物','得物','Expenses:Shopping',1),(1532,'2024-10-18 16:58:05.447799','2024-10-18 16:58:05.447847','拼多多','拼多多','Expenses:Shopping',1),(1533,'2024-10-18 16:58:05.454228','2024-10-18 16:58:05.454269','移动','中国移动','Assets:Savings:Recharge:Operator:Mobile:C6428',1),(1534,'2024-10-18 16:58:05.461009','2024-10-18 16:58:05.461081','电信','中国电信','Assets:Savings:Recharge:Operator:Telecom:C6428',1),(1535,'2024-10-18 16:58:05.467903','2024-10-18 16:58:05.467980','联通','中国联通','Assets:Savings:Recharge:Operator:Unicom:C6428',1),(1536,'2024-10-18 16:58:05.477070','2024-10-18 16:58:05.477180','深圳市腾讯计算机系统有限公司','','Expenses:Culture',1),(1537,'2024-10-18 16:58:05.484567','2024-10-18 16:58:05.484635','胖哥俩','胖哥俩','Expenses:Food',1),(1538,'2024-10-18 16:58:05.491276','2024-10-18 16:58:05.491339','服装','','Expenses:Shopping:Clothing',1),(1539,'2024-10-18 16:58:05.497928','2024-10-18 16:58:05.497956','衣服','','Expenses:Shopping:Clothing',1),(1540,'2024-10-18 16:58:05.505899','2024-10-18 16:58:05.505960','裤子','','Expenses:Shopping:Clothing',1),(1541,'2024-10-18 16:58:05.514167','2024-10-18 16:58:05.514227','鞋子','','Expenses:Shopping:Clothing',1),(1542,'2024-10-18 16:58:05.522239','2024-10-18 16:58:05.522325','袜子','','Expenses:Shopping:Clothing',1),(1543,'2024-10-18 16:58:05.530626','2024-10-18 16:58:05.530718','华为软件技术有限公司','华为','Expenses:Culture:Subscription',1),(1544,'2024-10-18 16:58:05.538652','2024-10-18 16:58:05.538715','淘宝','淘宝','Expenses:Shopping',1),(1545,'2024-10-18 16:58:05.547422','2024-10-18 16:58:05.547487','医保','','Expenses:Health',1),(1546,'2024-10-18 16:58:05.554174','2024-10-18 16:58:05.554226','自动续费','','Expenses:Culture:Subscription',1),(1547,'2024-10-18 16:58:05.561663','2024-10-18 16:58:05.561736','诊疗','','Expenses:Health',1),(1548,'2024-10-18 16:58:05.570448','2024-10-18 16:58:05.570510','卫生','','Expenses:Health',1),(1549,'2024-10-18 16:58:05.578226','2024-10-18 16:58:05.578302','统一公共支付平台','','Expenses:Government',1),(1550,'2024-10-18 16:58:05.586927','2024-10-18 16:58:05.587003','彩票','','Expenses:Culture',1),(1551,'2024-10-18 16:58:05.594875','2024-10-18 16:58:05.594916','超市','','Expenses:Shopping',1),(1552,'2024-10-18 16:58:05.603312','2024-10-18 16:58:05.603382','大润发','','Expenses:Shopping',1),(1553,'2024-10-18 16:58:05.611053','2024-10-18 16:58:05.611147','便利店','','Expenses:Shopping',1),(1554,'2024-10-18 16:58:05.620410','2024-10-18 16:58:05.620474','兰州拉面','兰州拉面','Expenses:Food',1),(1555,'2024-10-18 16:58:05.627119','2024-10-18 16:58:05.627194','供水','国家水网','Expenses:Home:Recharge',1),(1556,'2024-10-18 16:58:05.634866','2024-10-18 16:58:05.634944','绝味鸭脖','绝味鸭脖','Expenses:Food',1),(1557,'2024-10-18 16:58:05.643884','2024-10-18 16:58:05.643957','舒活食品','一鸣','Assets:Savings:Recharge:YiMing',1),(1558,'2024-10-18 16:58:05.651434','2024-10-18 16:58:05.651501','抖音生活服务','抖音','Expenses:Food',1),(1559,'2024-10-18 16:58:05.661177','2024-10-18 16:58:05.661246','医药','','Expenses:Health',1),(1560,'2024-10-18 16:58:05.669975','2024-10-18 16:58:05.670049','饮料','','Expenses:Food:DrinkFruit',1),(1561,'2024-10-18 16:58:05.678226','2024-10-18 16:58:05.678328','抖音月付','抖音','Liabilities:CreditCard:Web:DouYin',1),(1562,'2024-10-18 16:58:05.687574','2024-10-18 16:58:05.687671','公益','','Expenses:Culture',1),(1563,'2024-10-18 16:58:05.695121','2024-10-18 16:58:05.695196','等多件','','Expenses:Shopping',1),(1564,'2024-10-18 16:58:05.705331','2024-10-18 16:58:05.705413','喜茶','喜茶','Expenses:Food:DrinkFruit',1),(1565,'2024-10-18 16:58:05.713930','2024-10-18 16:58:05.714008','支付宝小荷包(戴某轩)','','Assets:Savings:Web:XiaoHeBao:DaiMouXuan',1),(1566,'2024-10-18 16:58:05.721970','2024-10-18 16:58:05.722033','倍耐力','','Expenses:TransPort:Private',1),(1567,'2024-10-18 16:58:05.730624','2024-10-18 16:58:05.730708','娱乐','','Expenses:Culture',1),(1568,'2024-10-18 16:58:05.738056','2024-10-18 16:58:05.738114','上海拉扎斯信息科技有限公司','饿了么','Expenses:Food',1),(1569,'2024-10-18 16:58:05.748430','2024-10-18 16:58:05.748509','夜宵','','Expenses:Food:Dinner',1),(1570,'2024-10-18 16:58:05.756637','2024-10-18 16:58:05.756694','打车','','Expenses:TransPort:Public',1),(1571,'2024-10-18 16:58:05.765123','2024-10-18 16:58:05.765203','抖音电商','抖音','Expenses:Shopping',1),(1572,'2024-10-18 16:58:05.772870','2024-10-18 16:58:05.772932','商城','','Expenses:Shopping',1),(1573,'2024-10-18 16:58:05.797003','2024-10-18 16:58:05.797088','保险','','Expenses:Finance:Insurance',1),(1574,'2024-10-18 16:58:05.806242','2024-10-18 16:58:05.806306','寄件','','Expenses:Home:Single',1),(1575,'2024-10-18 16:58:05.814948','2024-10-18 16:58:05.815035','书店','','Expenses:Culture',1),(1576,'2024-10-18 16:58:05.822678','2024-10-18 16:58:05.822736','外卖','','Expenses:Food',1),(1577,'2024-10-18 16:58:05.831498','2024-10-18 16:58:05.831574','滴滴出行','','Expenses:TransPort:Public',1),(1578,'2024-10-18 16:58:05.838394','2024-10-18 16:58:05.838460','公交','','Expenses:TransPort:Public',1),(1579,'2024-10-18 16:58:05.850935','2024-10-18 16:58:05.851049','航空','','Expenses:TransPort:Public',1),(1580,'2024-10-18 16:58:05.859183','2024-10-18 16:58:05.859240','储值','','Assets:Savings:Recharge',1),(1581,'2024-10-18 16:58:05.867333','2024-10-18 16:58:05.867394','出行','','Expenses:TransPort:Public',1),(1582,'2024-10-18 16:58:05.875710','2024-10-18 16:58:05.875789','下午茶','','Expenses:Food',1),(1583,'2024-10-18 16:58:05.883960','2024-10-18 16:58:05.884028','食物','','Expenses:Food',1),(1584,'2024-10-18 16:58:05.892570','2024-10-18 16:58:05.892636','午饭','','Expenses:Food:Lunch',1),(1585,'2024-10-18 16:58:05.902074','2024-10-18 16:58:05.902150','晚饭','','Expenses:Food:Dinner',1),(1586,'2024-10-18 16:58:05.911655','2024-10-18 16:58:05.911725','早饭','','Expenses:Food:Breakfast',1),(1587,'2024-10-18 16:58:05.919857','2024-10-18 16:58:05.919910','水费-','国家水网','Expenses:Home:Recharge',1),(1588,'2024-10-18 16:58:05.928061','2024-10-18 16:58:05.928133','电费-','国家电网','Expenses:Home:Recharge',1),(1589,'2024-10-18 16:58:05.936034','2024-10-18 16:58:05.936088','物流','','Expenses:Home',1),(1590,'2024-10-18 16:58:05.944607','2024-10-18 16:58:05.944673','快递','','Expenses:Home',1),(1591,'2024-10-18 16:58:05.952694','2024-10-18 16:58:05.952758','速递','','Expenses:Home',1),(1592,'2024-10-18 16:58:05.961373','2024-10-18 16:58:05.961446','App Store','','Expenses:Culture:Subscription',1),(1593,'2024-10-18 16:58:05.969253','2024-10-18 16:58:05.969315','饭店','','Expenses:Food',1),(1594,'2024-10-18 16:58:05.978680','2024-10-18 16:58:05.978769','面馆','','Expenses:Food',1),(1595,'2024-10-18 16:58:05.986794','2024-10-18 16:58:05.986879','服饰','','Expenses:Shopping:Clothing',1),(1596,'2024-10-18 16:58:05.995721','2024-10-18 16:58:05.995760','METRO','','Expenses:TransPort:Public',1),(1597,'2024-10-18 16:58:06.002146','2024-10-18 16:58:06.002210','食堂','','Expenses:Food',1),(1598,'2024-10-18 16:58:06.011192','2024-10-18 16:58:06.011221','生活缴费','','Expenses:Home',1),(1599,'2024-10-18 16:58:06.020989','2024-10-18 16:58:06.021013','速运','','Expenses:Home',1),(1600,'2024-10-18 16:58:06.028737','2024-10-18 16:58:06.028760','跑腿','','Expenses:Home',1),(1601,'2024-10-18 16:58:06.036011','2024-10-18 16:58:06.036030','霸王茶姬','霸王茶姬','Expenses:Food:DrinkFruit',1),(1602,'2024-10-18 16:58:06.041515','2024-10-18 16:58:06.041537','中医','','Expenses:Health',1),(1603,'2024-10-18 16:58:06.050521','2024-10-18 16:58:06.050542','理疗','','Expenses:Health',1),(1604,'2024-10-18 16:58:06.056622','2024-10-18 16:58:06.056661','肉粉馆','','Expenses:Food',1),(1605,'2024-10-18 16:58:06.064158','2024-10-18 16:58:06.064180','增值服务','','Expenses:Culture:Subscription',1),(1606,'2024-10-18 16:58:06.075534','2024-10-18 16:58:06.075555','购物','','Expenses:Shopping',1),(1607,'2024-10-18 16:58:06.081662','2024-10-18 16:58:06.081677','药业','','Expenses:Health:Medical',1),(1608,'2024-10-18 16:58:06.089228','2024-10-18 16:58:06.089247','药品','','Expenses:Health:Medical',1),(1609,'2024-10-18 16:58:06.096908','2024-10-18 16:58:06.096927','牙膏','','Expenses:Home:Daily',1),(1610,'2024-10-18 16:58:06.104372','2024-10-18 16:58:06.104387','运费','','Expenses:Home',1),(1611,'2024-10-18 16:58:06.112546','2024-10-18 16:58:06.112576','税务','','Expenses:Government',1),(1612,'2024-10-18 16:58:06.120598','2024-10-18 16:58:06.120636','充值','','Expenses:Home:Recharge',1),(1613,'2024-10-18 16:58:06.126569','2024-10-18 16:58:06.126600','订阅','','Expenses:Culture:Subscription',1),(1614,'2024-10-18 16:58:06.133975','2024-10-18 16:58:06.133997','轮胎','','Expenses:TransPort:Private',1),(1615,'2024-10-18 16:58:06.141480','2024-10-18 16:58:06.141504','服饰鞋包','','Expenses:Shopping:Clothing',1),(1616,'2024-10-18 16:58:06.149238','2024-10-18 16:58:06.149264','数码电器','','Expenses:Shopping:Digital',1),(1617,'2024-10-18 16:58:06.156734','2024-10-18 16:58:06.156753','美容美发','','Expenses:Shopping:Makeup',1),(1618,'2024-10-18 16:58:06.164803','2024-10-18 16:58:06.164827','母婴亲子','','Expenses:Shopping:Parent',1),(1619,'2024-10-18 16:58:06.170603','2024-10-18 16:58:06.170624','日用百货','','Expenses:Home:Daily',1),(1620,'2024-10-18 16:58:06.178512','2024-10-18 16:58:06.178547','门诊','','Expenses:Health',1),(1621,'2024-10-18 16:58:06.186475','2024-10-18 16:58:06.186499','挂号','','Expenses:Health',1),(1622,'2024-10-18 16:58:06.193833','2024-10-18 16:58:06.193857','体检','','Expenses:Health',1),(1623,'2024-10-18 16:58:06.201687','2024-10-18 16:58:06.201698','燃气','','Expenses:Home:Recharge',1),(1624,'2024-10-18 16:58:06.210390','2024-10-18 16:58:06.210412','装修','','Expenses:Home:Decoration',1),(1625,'2024-10-18 16:58:06.216290','2024-10-18 16:58:06.216315','科沃斯','科沃斯','Expenses:Shopping:Digital',1),(1626,'2024-10-18 16:58:06.222306','2024-10-18 16:58:06.222331','机器人','','Expenses:Shopping:Digital',1),(1627,'2024-10-18 16:58:06.228250','2024-10-18 16:58:06.228273','路由器','','Expenses:Shopping:Digital',1),(1628,'2024-10-18 16:58:06.233658','2024-10-18 16:58:06.233668','批发','','Expenses:Shopping',1),(1629,'2024-10-18 16:58:06.241293','2024-10-18 16:58:06.241309','小卖部','','Expenses:Shopping',1),(1630,'2024-10-18 16:58:06.246973','2024-10-18 16:58:06.246998','烧烤','','Expenses:Food',1),(1631,'2024-10-18 16:58:06.252781','2024-10-18 16:58:06.252807','排档','','Expenses:Food',1),(1632,'2024-10-18 16:58:06.260908','2024-10-18 16:58:06.260962','洗面奶','','Expenses:Shopping:Makeup',1),(1633,'2024-10-18 16:58:06.268959','2024-10-18 16:58:06.269017','婴儿','','Expenses:Shopping:Parent',1),(1634,'2024-10-18 16:58:06.277178','2024-10-18 16:58:06.277261','新生儿','','Expenses:Shopping:Parent',1),(1635,'2024-10-18 16:58:06.284953','2024-10-18 16:58:06.285026','宝宝','','Expenses:Shopping:Parent',1),(1636,'2024-10-18 16:58:06.293915','2024-10-18 16:58:06.293982','狂欢价','','Expenses:Shopping',1),(1637,'2024-10-18 16:58:06.301417','2024-10-18 16:58:06.301486','文具','','Expenses:Culture',1),(1638,'2024-10-18 16:58:06.310711','2024-10-18 16:58:06.310788','借出','','Assets:Receivables:Personal',1),(1639,'2024-10-18 16:58:06.317610','2024-10-18 16:58:06.317670','六贤记','六贤记','Assets:Savings:Recharge:LiuXianJi',1),(1640,'2024-10-18 16:58:06.326021','2024-10-18 16:58:06.326079','公共交通','','Expenses:TransPort:Public',1),(1641,'2024-10-18 16:58:06.333914','2024-10-18 16:58:06.333971','美团订单','美团','Expenses:Food',1);
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
  `key` varchar(16) NOT NULL,
  `payer` varchar(8) DEFAULT NULL,
  `income` varchar(64) NOT NULL,
  `owner_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `maps_income_owner_id_72c1c0ab_fk_auth_user_id` (`owner_id`),
  CONSTRAINT `maps_income_owner_id_72c1c0ab_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=39 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_income`
--

LOCK TABLES `maps_income` WRITE;
/*!40000 ALTER TABLE `maps_income` DISABLE KEYS */;
INSERT INTO `maps_income` VALUES (32,'2024-10-18 16:58:10.720217','2024-10-18 16:58:10.720255','红包',NULL,'Income:Receivables:RedPacket',1),(33,'2024-10-18 16:58:10.726582','2024-10-18 16:58:10.726631','某义','老婆','Liabilities:Payables:Personal:LaoPo',1),(34,'2024-10-18 16:58:10.735493','2024-10-18 16:58:10.735618','小荷包',NULL,'Assets:Savings:Web:XiaoHeBao',1),(35,'2024-10-18 16:58:10.743159','2024-10-18 16:58:10.743284','老婆','老婆','Liabilities:Payables:Personal:LaoPo',1),(36,'2024-10-18 16:58:10.751967','2024-10-18 16:58:10.751998','戴某轩',NULL,'Assets:Savings:Web:XiaoHeBao:DaiMouXuan',1),(37,'2024-10-18 16:58:10.759864','2024-10-18 16:58:10.759915','收钱码经营版收款',NULL,'Income:Business',1),(38,'2024-10-18 16:58:10.767807','2024-10-18 16:58:10.767839','出行账户余额提现',NULL,'Income:Sideline:DiDi',1);
/*!40000 ALTER TABLE `maps_income` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `mfa_authenticator`
--

DROP TABLE IF EXISTS `mfa_authenticator`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mfa_authenticator` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `type` varchar(20) NOT NULL,
  `data` json NOT NULL,
  `user_id` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `last_used_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `mfa_authenticator_user_id_0c3a50c0` (`user_id`),
  CONSTRAINT `mfa_authenticator_user_id_0c3a50c0_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `mfa_authenticator`
--

LOCK TABLES `mfa_authenticator` WRITE;
/*!40000 ALTER TABLE `mfa_authenticator` DISABLE KEYS */;
/*!40000 ALTER TABLE `mfa_authenticator` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `owntracks_owntracklog`
--

DROP TABLE IF EXISTS `owntracks_owntracklog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `owntracks_owntracklog` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tid` varchar(100) NOT NULL,
  `lat` double NOT NULL,
  `lon` double NOT NULL,
  `creation_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `owntracks_owntracklog`
--

LOCK TABLES `owntracks_owntracklog` WRITE;
/*!40000 ALTER TABLE `owntracks_owntracklog` DISABLE KEYS */;
/*!40000 ALTER TABLE `owntracks_owntracklog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `socialaccount_socialaccount`
--

DROP TABLE IF EXISTS `socialaccount_socialaccount`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `socialaccount_socialaccount` (
  `id` int NOT NULL AUTO_INCREMENT,
  `provider` varchar(200) NOT NULL,
  `uid` varchar(191) NOT NULL,
  `last_login` datetime(6) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `extra_data` json NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `socialaccount_socialaccount_provider_uid_fc810c6e_uniq` (`provider`,`uid`),
  KEY `socialaccount_socialaccount_user_id_8146e70c_fk_auth_user_id` (`user_id`),
  CONSTRAINT `socialaccount_socialaccount_user_id_8146e70c_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `socialaccount_socialaccount`
--

LOCK TABLES `socialaccount_socialaccount` WRITE;
/*!40000 ALTER TABLE `socialaccount_socialaccount` DISABLE KEYS */;
/*!40000 ALTER TABLE `socialaccount_socialaccount` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `socialaccount_socialapp`
--

DROP TABLE IF EXISTS `socialaccount_socialapp`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `socialaccount_socialapp` (
  `id` int NOT NULL AUTO_INCREMENT,
  `provider` varchar(30) NOT NULL,
  `name` varchar(40) NOT NULL,
  `client_id` varchar(191) NOT NULL,
  `secret` varchar(191) NOT NULL,
  `key` varchar(191) NOT NULL,
  `provider_id` varchar(200) NOT NULL,
  `settings` json NOT NULL DEFAULT (_utf8mb3'{}'),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `socialaccount_socialapp`
--

LOCK TABLES `socialaccount_socialapp` WRITE;
/*!40000 ALTER TABLE `socialaccount_socialapp` DISABLE KEYS */;
/*!40000 ALTER TABLE `socialaccount_socialapp` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `socialaccount_socialapp_sites`
--

DROP TABLE IF EXISTS `socialaccount_socialapp_sites`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `socialaccount_socialapp_sites` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `socialapp_id` int NOT NULL,
  `site_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `socialaccount_socialapp_sites_socialapp_id_site_id_71a9a768_uniq` (`socialapp_id`,`site_id`),
  KEY `socialaccount_socialapp_sites_site_id_2579dee5_fk_django_site_id` (`site_id`),
  CONSTRAINT `socialaccount_social_socialapp_id_97fb6e7d_fk_socialacc` FOREIGN KEY (`socialapp_id`) REFERENCES `socialaccount_socialapp` (`id`),
  CONSTRAINT `socialaccount_socialapp_sites_site_id_2579dee5_fk_django_site_id` FOREIGN KEY (`site_id`) REFERENCES `django_site` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `socialaccount_socialapp_sites`
--

LOCK TABLES `socialaccount_socialapp_sites` WRITE;
/*!40000 ALTER TABLE `socialaccount_socialapp_sites` DISABLE KEYS */;
/*!40000 ALTER TABLE `socialaccount_socialapp_sites` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `socialaccount_socialtoken`
--

DROP TABLE IF EXISTS `socialaccount_socialtoken`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `socialaccount_socialtoken` (
  `id` int NOT NULL AUTO_INCREMENT,
  `token` longtext NOT NULL,
  `token_secret` longtext NOT NULL,
  `expires_at` datetime(6) DEFAULT NULL,
  `account_id` int NOT NULL,
  `app_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `socialaccount_socialtoken_app_id_account_id_fca4e0ac_uniq` (`app_id`,`account_id`),
  KEY `socialaccount_social_account_id_951f210e_fk_socialacc` (`account_id`),
  CONSTRAINT `socialaccount_social_account_id_951f210e_fk_socialacc` FOREIGN KEY (`account_id`) REFERENCES `socialaccount_socialaccount` (`id`),
  CONSTRAINT `socialaccount_social_app_id_636a42d7_fk_socialacc` FOREIGN KEY (`app_id`) REFERENCES `socialaccount_socialapp` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `socialaccount_socialtoken`
--

LOCK TABLES `socialaccount_socialtoken` WRITE;
/*!40000 ALTER TABLE `socialaccount_socialtoken` DISABLE KEYS */;
/*!40000 ALTER TABLE `socialaccount_socialtoken` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usersessions_usersession`
--

DROP TABLE IF EXISTS `usersessions_usersession`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usersessions_usersession` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `ip` char(39) NOT NULL,
  `last_seen_at` datetime(6) NOT NULL,
  `session_key` varchar(40) NOT NULL,
  `user_agent` varchar(200) NOT NULL,
  `data` json NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `session_key` (`session_key`),
  KEY `usersessions_usersession_user_id_af5e0a6d_fk_auth_user_id` (`user_id`),
  CONSTRAINT `usersessions_usersession_user_id_af5e0a6d_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=167 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usersessions_usersession`
--

LOCK TABLES `usersessions_usersession` WRITE;
/*!40000 ALTER TABLE `usersessions_usersession` DISABLE KEYS */;
/*!40000 ALTER TABLE `usersessions_usersession` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-10-18 16:58:43

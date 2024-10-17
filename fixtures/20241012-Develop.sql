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

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `beancount-trans` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

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
INSERT INTO `account_emailaddress` VALUES (3,'dai_haorui@163.com',1,1,1),(5,'dhr2diary@gmail.com',0,0,1),(13,'email@domain.org',0,1,34),(25,'a13738756428@gmail.com',1,1,48);
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
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
INSERT INTO `auth_user` VALUES (1,'pbkdf2_sha256$870000$xfIF9Gwx9ebDXNvSONK5ud$SK+3hlTGgD2lUmia7tluijWCXgOicrEa8Ooexrkj7Nc=','2024-10-11 08:04:37.585101',1,'daihaorui','','','dhr2diary@gmail.com',1,1,'2024-08-19 10:49:00.000000'),(34,'pbkdf2_sha256$870000$eSmWeUIr8QzGfBaTJjxscJ$19UcxTDxDhEvtUl9BKh0SOFJ2we+vOVx7xCFwf2aSdo=',NULL,0,'wizard','','','email@domain.org',0,1,'2024-09-30 10:22:59.908813'),(47,'!3bsMd6ryPVprfIi6ZSl3rg7F2Bz7sqbyqWckNxbp','2024-10-10 15:30:31.131353',1,'dhr2333','daihaorui','','',1,1,'2024-10-10 09:22:00.000000'),(48,'!6hxeG2ZM9jWs9c5RGPHrc48J7Xm9pIUtxcxJp2WK','2024-10-11 08:03:10.740839',0,'a13738756428','豪锐','戴','a13738756428@gmail.com',0,1,'2024-10-10 15:31:13.197986');
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
INSERT INTO `authtoken_token` VALUES ('7011f4a8380fb9d7f466c205c1dda0c7e52b5f45','2024-08-29 16:03:00.225877',1);
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
) ENGINE=InnoDB AUTO_INCREMENT=86 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
INSERT INTO `django_admin_log` VALUES (1,'2024-08-19 11:22:25.276862','2','admin',3,'',4,1),(2,'2024-08-19 11:22:25.283642','4','admin1',3,'',4,1),(3,'2024-08-19 11:22:25.290191','5','daihaorui2',3,'',4,1),(4,'2024-08-19 11:22:25.298730','3','user1',3,'',4,1),(5,'2024-08-19 11:22:47.881828','1','admin',2,'[{\"changed\": {\"fields\": [\"Username\", \"Last login\"]}}]',4,1),(6,'2024-08-19 13:30:46.860069','7','daihaorui1',3,'',4,1),(7,'2024-08-20 09:50:08.450845','3','dai_haorui@163.com',2,'[{\"changed\": {\"fields\": [\"Verified\"]}}]',14,1),(8,'2024-08-20 09:50:28.147035','6','daihaorui',2,'[{\"changed\": {\"fields\": [\"Email address\", \"Last login\"]}}]',4,1),(9,'2024-08-20 09:50:40.902119','6','daihaorui',2,'[{\"changed\": {\"fields\": [\"Email address\"]}}]',4,1),(10,'2024-08-27 11:16:17.729258','1','Google',1,'[{\"added\": {}}]',17,1),(11,'2024-08-27 13:24:19.828661','2','GitHub',1,'[{\"added\": {}}]',17,1),(12,'2024-08-27 14:15:08.692672','1','Google',2,'[]',17,1),(13,'2024-08-27 14:17:12.315476','2','GitHub',3,'',17,1),(14,'2024-08-27 14:17:20.019817','2','daihaorui',3,'',16,1),(15,'2024-08-27 14:17:29.543298','6','daihaorui',3,'',4,1),(16,'2024-08-27 14:29:04.347066','1','Google',2,'[{\"changed\": {\"fields\": [\"Sites\"]}}]',17,1),(17,'2024-08-27 14:31:18.971772','3','GitHub',1,'[{\"added\": {}}]',17,1),(18,'2024-08-27 14:33:26.701646','9','daihaorui',2,'[{\"changed\": {\"fields\": [\"Staff status\", \"Superuser status\", \"Last login\"]}}]',4,1),(19,'2024-08-27 14:33:41.175459','8','haorui',2,'[{\"changed\": {\"fields\": [\"Staff status\", \"Superuser status\", \"Last login\"]}}]',4,1),(20,'2024-08-27 14:45:21.240161','9','daihaorui',2,'[{\"changed\": {\"fields\": [\"Email address\"]}}]',4,1),(21,'2024-08-27 14:45:31.308351','1','admin',2,'[{\"changed\": {\"fields\": [\"Email address\", \"Last login\"]}}]',4,1),(22,'2024-08-29 09:40:26.637765','10','email',3,'',4,1),(23,'2024-08-29 09:44:16.596757','11','email',3,'',4,1),(24,'2024-08-29 09:59:32.262118','24','email',3,'',4,1),(25,'2024-08-29 10:01:15.607427','25','email',3,'',4,1),(43,'2024-08-29 15:58:28.797515','6','haorui',3,'',16,1),(44,'2024-08-29 15:58:28.797575','5','daihaorui9',3,'',16,1),(45,'2024-08-29 16:00:32.750685','8','haorui7',3,'',16,1),(46,'2024-08-29 16:00:53.977853','7','daihaorui4',3,'',16,1),(47,'2024-08-29 16:02:41.851843','29','daihaorui4',3,'',4,1),(48,'2024-08-29 16:02:41.851867','27','daihaorui9',3,'',4,1),(49,'2024-08-29 16:02:41.851877','28','haorui',3,'',4,1),(50,'2024-08-29 16:02:41.851885','30','haorui7',3,'',4,1),(51,'2024-08-29 16:03:00.226204','1','7011f4a8380fb9d7f466c205c1dda0c7e52b5f45',1,'[{\"added\": {}}]',13,1),(52,'2024-08-29 16:04:48.684767','9','daihaorui',3,'',4,1),(53,'2024-08-30 09:19:22.869259','10','admin',3,'',16,1),(54,'2024-08-31 14:58:53.720417','11','daihaorui',3,'',16,1),(55,'2024-08-31 15:07:22.669160','32','b9c2e1f693906d6746cf66a98d1dd19df3bdd9e5',3,'',13,1),(56,'2024-08-31 15:16:52.363563','32','daihaorui',3,'',4,1),(57,'2024-08-31 15:16:52.363588','31','user',3,'',4,1),(58,'2024-08-31 15:24:13.621052','9','admin',3,'',16,1),(59,'2024-09-10 13:15:38.993610','1','daihaorui',2,'[{\"changed\": {\"fields\": [\"Username\", \"Last login\"]}}]',4,1),(60,'2024-10-07 16:22:07.158833','14','a13738756428',3,'',16,1),(61,'2024-10-07 16:22:59.381534','36','01wizard',3,'',4,1),(62,'2024-10-07 16:22:59.381556','35','1wizard',3,'',4,1),(63,'2024-10-07 16:22:59.381564','37','a13738756428',3,'',4,1),(64,'2024-10-08 11:23:57.885723','38','a13738756428',3,'',4,1),(65,'2024-10-08 12:56:41.115862','39','a13738756428',3,'',4,1),(66,'2024-10-08 13:11:03.095392','40','a13738756428',3,'',4,1),(67,'2024-10-08 13:13:11.961440','41','a13738756428',2,'[{\"changed\": {\"fields\": [\"Staff status\", \"Superuser status\", \"Last login\"]}}]',4,1),(68,'2024-10-08 13:19:47.730699','41','a13738756428',3,'',4,1),(69,'2024-10-08 13:27:34.638934','42','a13738756428',3,'',4,1),(70,'2024-10-08 13:28:21.150322','43','a13738756428',3,'',4,1),(71,'2024-10-09 13:32:11.054569','44','1',3,'',4,1),(72,'2024-10-10 08:53:04.504461','1','Google',3,'',17,1),(73,'2024-10-10 08:53:57.779049','3','GitHub',3,'',17,1),(74,'2024-10-10 08:54:06.936822','13','daihaorui',3,'',16,1),(75,'2024-10-10 08:54:06.936899','12','dhr2333',3,'',16,1),(76,'2024-10-10 09:01:43.181789','4','Google',1,'[{\"added\": {}}]',17,1),(77,'2024-10-10 09:14:22.104167','4','Google',3,'',17,1),(78,'2024-10-10 09:15:24.031049','22','a13738756428',3,'',16,1),(79,'2024-10-10 09:18:35.922164','45','a13738756428',3,'',4,1),(80,'2024-10-10 09:18:35.922188','33','dhr2333',3,'',4,1),(81,'2024-10-10 09:21:34.089989','23','a13738756428',3,'',16,1),(82,'2024-10-10 15:30:16.862895','47','dhr2333',2,'[{\"changed\": {\"fields\": [\"Staff status\", \"Superuser status\", \"Last login\"]}}]',4,1),(83,'2024-10-10 15:30:58.955980','46','a13738756428',3,'',4,47),(84,'2024-10-11 08:05:16.795577','3','http://127.0.0.1:8002/',1,'[{\"added\": {}}]',7,1),(85,'2024-10-11 08:05:30.275390','4','http://localhost:5173/',1,'[{\"added\": {}}]',7,1);
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
) ENGINE=InnoDB AUTO_INCREMENT=133 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_assets`
--

LOCK TABLES `maps_assets` WRITE;
/*!40000 ALTER TABLE `maps_assets` DISABLE KEYS */;
INSERT INTO `maps_assets` VALUES (111,'2024-08-19 15:53:10.716897','2024-08-19 15:53:10.716940','5522','中国建设银行储蓄卡(5522)',1,'Assets:Savings:Bank:CCB:C5522'),(112,'2024-08-19 15:53:10.723841','2024-08-19 15:53:10.723890','6428','中信银行信用卡(6428)',1,'Liabilities:CreditCard:Bank:CITIC:C6428'),(113,'2024-08-19 15:53:10.730498','2024-08-19 15:53:10.730539','零钱通','微信零钱通',1,'Assets:Savings:Web:WechatFund'),(114,'2024-08-19 15:53:10.738157','2024-08-19 15:53:10.738193','零钱','微信零钱',1,'Assets:Savings:Web:WechatPay'),(115,'2024-08-19 15:53:10.746838','2024-08-19 15:53:10.746889','/','微信零钱',1,'Assets:Savings:Web:WechatPay'),(116,'2024-08-19 15:53:10.753664','2024-08-19 15:53:10.753728','8837','中国招商银行储蓄卡(8837)',1,'Assets:Savings:Bank:CMB:C8837'),(117,'2024-08-19 15:53:10.761035','2024-08-19 15:53:10.761089','1746','宁波银行储蓄卡(1746)',1,'Assets:Savings:Bank:NBCB:C1746'),(118,'2024-08-19 15:53:10.768230','2024-08-19 15:53:10.768310','8273','中国农业银行储蓄卡(8273)',1,'Assets:Savings:Bank:ABC:C8273'),(119,'2024-08-19 15:53:10.775978','2024-08-19 15:53:10.776036','7651','中国工商银行储蓄卡(7651)',1,'Assets:Savings:Bank:ICBC:C7651'),(120,'2024-08-19 15:53:10.787699','2024-08-19 15:53:10.787793','5244','中国工商银行储蓄卡(5244)',1,'Assets:Savings:Bank:ICBC:C5244'),(121,'2024-08-19 15:53:10.796573','2024-08-19 15:53:10.796646','5636','华夏银行储蓄卡(5636)',1,'Assets:Savings:Bank:HXB:C5636'),(122,'2024-08-19 15:53:10.804622','2024-08-19 15:53:10.804686','余额宝','支付宝余额宝',1,'Assets:Savings:Web:AliFund'),(123,'2024-08-19 15:53:10.813645','2024-08-19 15:53:10.813713','余额','支付宝余额',1,'Assets:Savings:Web:AliPay'),(124,'2024-08-19 15:53:10.822001','2024-08-19 15:53:10.822074','戴豪轩','小荷包(戴豪轩)',1,'Assets:Savings:Web:XiaoHeBao:DaiHaoXuan'),(125,'2024-08-19 15:53:10.831891','2024-08-19 15:53:10.831948','账户余额','支付宝余额',1,'Assets:Savings:Web:AliPay'),(126,'2024-08-19 15:53:10.841366','2024-08-19 15:53:10.841443','花呗','支付宝花呗',1,'Liabilities:CreditCard:Web:HuaBei'),(127,'2024-08-19 15:53:10.850745','2024-08-19 15:53:10.850810','4523','中国招商银行信用卡(4523)',1,'Liabilities:CreditCard:Bank:CMB:C4523'),(128,'2024-08-19 15:53:10.858567','2024-08-19 15:53:10.858676','8313','中国招商银行信用卡(8313)',1,'Liabilities:CreditCard:Bank:CMB:C8313'),(129,'2024-08-19 15:53:10.867769','2024-08-19 15:53:10.867843','9813','中国招商银行信用卡(9813)',1,'Liabilities:CreditCard:Bank:CMB:C9813'),(130,'2024-08-19 15:53:10.875957','2024-08-19 15:53:10.876024','0005','浙江农商银行储蓄卡(0005)',1,'Assets:Savings:Bank:ZJRCUB:C0005'),(131,'2024-08-19 15:53:10.887074','2024-08-19 15:53:10.887167','0814','中国银行储蓄卡(0814)',1,'Assets:Savings:Bank:BOC:C0814'),(132,'2024-08-19 15:53:10.896565','2024-08-19 15:53:10.896737','4144','中国光大银行储蓄卡(4144)',1,'Assets:Savings:Bank:CEB:C4144');
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
) ENGINE=InnoDB AUTO_INCREMENT=1286 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_expense`
--

LOCK TABLES `maps_expense` WRITE;
/*!40000 ALTER TABLE `maps_expense` DISABLE KEYS */;
INSERT INTO `maps_expense` VALUES (1107,'2024-08-19 15:53:33.732330','2024-08-19 15:53:33.732362','蜜雪冰城','蜜雪冰城','Expenses:Food:DrinkFruit',1),(1108,'2024-08-19 15:53:33.738793','2024-08-19 15:53:33.738829','停车','','Expenses:TransPort:Private:Park',1),(1109,'2024-08-19 15:53:33.748446','2024-08-19 15:53:33.748490','浙C','','Expenses:TransPort:Private:Park',1),(1110,'2024-08-19 15:53:33.758622','2024-08-19 15:53:33.758702','鲜花','','Expenses:Culture',1),(1111,'2024-08-19 15:53:33.767116','2024-08-19 15:53:33.767176','古茗','','Expenses:Food:DrinkFruit',1),(1112,'2024-08-19 15:53:33.776260','2024-08-19 15:53:33.776331','益味坊','','Expenses:Food:Breakfast',1),(1113,'2024-08-19 15:53:33.783748','2024-08-19 15:53:33.783799','塔斯汀','塔斯汀','Expenses:Food',1),(1114,'2024-08-19 15:53:33.793525','2024-08-19 15:53:33.793601','十足','十足','Expenses:Food',1),(1115,'2024-08-19 15:53:33.802557','2024-08-19 15:53:33.802620','一点点','一点点','Expenses:Food:DrinkFruit',1),(1116,'2024-08-19 15:53:33.813515','2024-08-19 15:53:33.813591','luckin','瑞幸','Expenses:Food:DrinkFruit',1),(1117,'2024-08-19 15:53:33.821725','2024-08-19 15:53:33.821792','娘娘大人','娘娘大人','Expenses:Food',1),(1118,'2024-08-19 15:53:33.831209','2024-08-19 15:53:33.831285','老婆大人','老婆大人','Assets:Savings:Recharge:LaoPoDaRen',1),(1119,'2024-08-19 15:53:33.839464','2024-08-19 15:53:33.839541','茶百道','茶百道','Expenses:Food:DrinkFruit',1),(1120,'2024-08-19 15:53:33.848436','2024-08-19 15:53:33.848504','京东','京东','Expenses:Shopping',1),(1121,'2024-08-19 15:53:33.856741','2024-08-19 15:53:33.856819','包月','','Expenses:Culture:Subscription',1),(1122,'2024-08-19 15:53:33.865629','2024-08-19 15:53:33.865705','正新鸡排','','Expenses:Food',1),(1123,'2024-08-19 15:53:33.875532','2024-08-19 15:53:33.875602','奇虎智能','','Expenses:Shopping:Digital',1),(1124,'2024-08-19 15:53:33.884857','2024-08-19 15:53:33.884923','Petal On','华为','Expenses:Culture:Subscription',1),(1125,'2024-08-19 15:53:33.892464','2024-08-19 15:53:33.892549','药房','','Expenses:Health:Medical',1),(1126,'2024-08-19 15:53:33.901063','2024-08-19 15:53:33.901128','药店','','Expenses:Health:Medical',1),(1127,'2024-08-19 15:53:33.909739','2024-08-19 15:53:33.909818','医院','','Expenses:Health',1),(1128,'2024-08-19 15:53:33.918208','2024-08-19 15:53:33.918275','餐饮','','Expenses:Food',1),(1129,'2024-08-19 15:53:33.927314','2024-08-19 15:53:33.927391','食品','','Expenses:Food',1),(1130,'2024-08-19 15:53:33.940327','2024-08-19 15:53:33.940398','深圳市腾讯天游科技有限公司','','Expenses:Culture:Entertainment',1),(1131,'2024-08-19 15:53:33.949179','2024-08-19 15:53:33.949255','水果','','Expenses:Food:DrinkFruit',1),(1132,'2024-08-19 15:53:33.957478','2024-08-19 15:53:33.957552','早餐','','Expenses:Food:Breakfast',1),(1133,'2024-08-19 15:53:33.966296','2024-08-19 15:53:33.966364','充电','','Expenses:TransPort:Private:Fuel',1),(1134,'2024-08-19 15:53:33.974872','2024-08-19 15:53:33.974942','加油','','Expenses:TransPort:Private:Fuel',1),(1135,'2024-08-19 15:53:33.983240','2024-08-19 15:53:33.983404','供电局','国家电网','Expenses:Home:Recharge',1),(1136,'2024-08-19 15:53:33.991870','2024-08-19 15:53:33.991942','ETC','','Expenses:TransPort:Public',1),(1137,'2024-08-19 15:53:34.000557','2024-08-19 15:53:34.000613','华为终端有限公司','华为','Expenses:Shopping:Digital',1),(1138,'2024-08-19 15:53:34.009238','2024-08-19 15:53:34.009299','饿了么','饿了么','Expenses:Food',1),(1139,'2024-08-19 15:53:34.016921','2024-08-19 15:53:34.016989','美团平台商户','美团','Expenses:Food',1),(1140,'2024-08-19 15:53:34.025989','2024-08-19 15:53:34.026061','地铁','','Expenses:TransPort:Public',1),(1141,'2024-08-19 15:53:34.038923','2024-08-19 15:53:34.038988','国网智慧车联网','国家电网','Expenses:TransPort:Private:Fuel',1),(1142,'2024-08-19 15:53:34.047015','2024-08-19 15:53:34.047108','肯德基','肯德基','Expenses:Food',1),(1143,'2024-08-19 15:53:34.055814','2024-08-19 15:53:34.055860','华为','华为','Expenses:Shopping',1),(1144,'2024-08-19 15:53:34.064223','2024-08-19 15:53:34.064291','沙县小吃','沙县小吃','Expenses:Food',1),(1145,'2024-08-19 15:53:34.071869','2024-08-19 15:53:34.071903','一鸣','一鸣','Expenses:Food',1),(1146,'2024-08-19 15:53:34.077866','2024-08-19 15:53:34.077883','之上','之上','Expenses:Food',1),(1147,'2024-08-19 15:53:34.085634','2024-08-19 15:53:34.085668','大疆','','Expenses:Shopping:Digital',1),(1148,'2024-08-19 15:53:34.094083','2024-08-19 15:53:34.094146','12306','12306','Expenses:TransPort:Public',1),(1149,'2024-08-19 15:53:34.101747','2024-08-19 15:53:34.101804','阿里云','阿里云','Expenses:Culture:Subscription',1),(1150,'2024-08-19 15:53:34.111107','2024-08-19 15:53:34.111172','电影','','Expenses:Culture:Entertainment',1),(1151,'2024-08-19 15:53:34.118076','2024-08-19 15:53:34.118125','火车票','','Expenses:TransPort:Public',1),(1152,'2024-08-19 15:53:34.125066','2024-08-19 15:53:34.125139','高铁','','Expenses:TransPort:Public',1),(1153,'2024-08-19 15:53:34.133023','2024-08-19 15:53:34.133089','机票','','Expenses:TransPort:Public',1),(1154,'2024-08-19 15:53:34.141918','2024-08-19 15:53:34.142010','医疗','','Expenses:Health',1),(1155,'2024-08-19 15:53:34.148991','2024-08-19 15:53:34.149037','医生','','Expenses:Health',1),(1156,'2024-08-19 15:53:34.155949','2024-08-19 15:53:34.156021','医用','','Expenses:Health',1),(1157,'2024-08-19 15:53:34.163657','2024-08-19 15:53:34.163725','小吃','','Expenses:Food',1),(1158,'2024-08-19 15:53:34.180933','2024-08-19 15:53:34.181010','餐厅','','Expenses:Food',1),(1159,'2024-08-19 15:53:34.192434','2024-08-19 15:53:34.192521','小食','','Expenses:Food',1),(1160,'2024-08-19 15:53:34.201041','2024-08-19 15:53:34.201122','旗舰店','淘宝','Expenses:Shopping',1),(1161,'2024-08-19 15:53:34.209849','2024-08-19 15:53:34.209927','粮粮驾到','粮粮驾到','Assets:Savings:Recharge:LiangLiangJiaDao',1),(1162,'2024-08-19 15:53:34.218872','2024-08-19 15:53:34.218951','中国石油','中国石油','Expenses:TransPort:Private:Fuel',1),(1163,'2024-08-19 15:53:34.227083','2024-08-19 15:53:34.227180','酒店','','Expenses:Culture',1),(1164,'2024-08-19 15:53:34.236041','2024-08-19 15:53:34.236109','凯义','老婆','Expenses:Relationship',1),(1165,'2024-08-19 15:53:34.244504','2024-08-19 15:53:34.244586','高德','高德','Expenses:TransPort:Public',1),(1166,'2024-08-19 15:53:34.252933','2024-08-19 15:53:34.253006','烟酒','','Expenses:Food:DrinkFruit',1),(1167,'2024-08-19 15:53:34.261794','2024-08-19 15:53:34.261873','理发','','Expenses:Shopping:Makeup',1),(1168,'2024-08-19 15:53:34.270219','2024-08-19 15:53:34.270311','美发','','Expenses:Shopping:Makeup',1),(1169,'2024-08-19 15:53:34.279865','2024-08-19 15:53:34.279960','美容','','Expenses:Shopping:Makeup',1),(1170,'2024-08-19 15:53:34.290307','2024-08-19 15:53:34.290393','华莱士','华莱士','Expenses:Food',1),(1171,'2024-08-19 15:53:34.300075','2024-08-19 15:53:34.300155','晚餐','','Expenses:Food:Dinner',1),(1172,'2024-08-19 15:53:34.308118','2024-08-19 15:53:34.308178','午餐','','Expenses:Food:Lunch',1),(1173,'2024-08-19 15:53:34.317778','2024-08-19 15:53:34.317861','新时沏','新时沏','Expenses:Food:DrinkFruit',1),(1174,'2024-08-19 15:53:34.327387','2024-08-19 15:53:34.327432','得物','得物','Expenses:Shopping',1),(1175,'2024-08-19 15:53:34.338814','2024-08-19 15:53:34.338838','拼多多','拼多多','Expenses:Shopping',1),(1176,'2024-08-19 15:53:34.346048','2024-08-19 15:53:34.346079','移动','中国移动','Assets:Savings:Recharge:Operator:Mobile:C6428',1),(1177,'2024-08-19 15:53:34.355808','2024-08-19 15:53:34.355862','电信','中国电信','Assets:Savings:Recharge:Operator:Telecom:C6428',1),(1178,'2024-08-19 15:53:34.363717','2024-08-19 15:53:34.363730','联通','中国联通','Assets:Savings:Recharge:Operator:Unicom:C6428',1),(1179,'2024-08-19 15:53:34.371887','2024-08-19 15:53:34.371914','深圳市腾讯计算机系统有限公司','','Expenses:Culture',1),(1180,'2024-08-19 15:53:34.378123','2024-08-19 15:53:34.378148','胖哥俩','胖哥俩','Expenses:Food',1),(1181,'2024-08-19 15:53:34.385812','2024-08-19 15:53:34.385829','服装','','Expenses:Shopping:Clothing',1),(1182,'2024-08-19 15:53:34.393385','2024-08-19 15:53:34.393406','衣服','','Expenses:Shopping:Clothing',1),(1183,'2024-08-19 15:53:34.401051','2024-08-19 15:53:34.401085','裤子','','Expenses:Shopping:Clothing',1),(1184,'2024-08-19 15:53:34.409182','2024-08-19 15:53:34.409210','鞋子','','Expenses:Shopping:Clothing',1),(1185,'2024-08-19 15:53:34.417380','2024-08-19 15:53:34.417408','袜子','','Expenses:Shopping:Clothing',1),(1186,'2024-08-19 15:53:34.424722','2024-08-19 15:53:34.424745','华为软件技术有限公司','华为','Expenses:Culture:Subscription',1),(1187,'2024-08-19 15:53:34.432681','2024-08-19 15:53:34.432709','淘宝','淘宝','Expenses:Shopping',1),(1188,'2024-08-19 15:53:34.440479','2024-08-19 15:53:34.440500','医保','','Expenses:Health',1),(1189,'2024-08-19 15:53:34.448039','2024-08-19 15:53:34.448066','自动续费','','Expenses:Culture:Subscription',1),(1190,'2024-08-19 15:53:34.455834','2024-08-19 15:53:34.455851','诊疗','','Expenses:Health',1),(1191,'2024-08-19 15:53:34.463212','2024-08-19 15:53:34.463226','卫生','','Expenses:Health',1),(1192,'2024-08-19 15:53:34.471492','2024-08-19 15:53:34.471532','统一公共支付平台','','Expenses:Government',1),(1193,'2024-08-19 15:53:34.477874','2024-08-19 15:53:34.477898','彩票','','Expenses:Culture',1),(1194,'2024-08-19 15:53:34.483992','2024-08-19 15:53:34.484015','超市','','Expenses:Shopping',1),(1195,'2024-08-19 15:53:34.492571','2024-08-19 15:53:34.492592','大润发','','Expenses:Shopping',1),(1196,'2024-08-19 15:53:34.498518','2024-08-19 15:53:34.498537','便利店','','Expenses:Shopping',1),(1197,'2024-08-19 15:53:34.505132','2024-08-19 15:53:34.505153','兰州拉面','兰州拉面','Expenses:Food',1),(1198,'2024-08-19 15:53:34.513132','2024-08-19 15:53:34.513153','供水','国家水网','Expenses:Home:Recharge',1),(1199,'2024-08-19 15:53:34.519377','2024-08-19 15:53:34.519405','绝味鸭脖','绝味鸭脖','Expenses:Food',1),(1200,'2024-08-19 15:53:34.525876','2024-08-19 15:53:34.525910','舒活食品','一鸣','Assets:Savings:Recharge:YiMing',1),(1201,'2024-08-19 15:53:34.532618','2024-08-19 15:53:34.532666','抖音生活服务','抖音','Expenses:Food',1),(1202,'2024-08-19 15:53:34.541185','2024-08-19 15:53:34.541250','医药','','Expenses:Health',1),(1203,'2024-08-19 15:53:34.548971','2024-08-19 15:53:34.549028','饮料','','Expenses:Food:DrinkFruit',1),(1204,'2024-08-19 15:53:34.557861','2024-08-19 15:53:34.557927','抖音月付','抖音','Liabilities:CreditCard:Web:DouYin',1),(1205,'2024-08-19 15:53:34.565669','2024-08-19 15:53:34.565718','公益','','Expenses:Culture',1),(1206,'2024-08-19 15:53:34.574326','2024-08-19 15:53:34.574386','等多件','','Expenses:Shopping',1),(1207,'2024-08-19 15:53:34.582094','2024-08-19 15:53:34.582144','喜茶','喜茶','Expenses:Food:DrinkFruit',1),(1208,'2024-08-19 15:53:34.591226','2024-08-19 15:53:34.591298','支付宝小荷包(戴豪轩)','','Assets:Savings:Web:XiaoHeBao:DaiHaoXuan',1),(1209,'2024-08-19 15:53:34.599111','2024-08-19 15:53:34.599178','倍耐力','','Expenses:TransPort:Private',1),(1210,'2024-08-19 15:53:34.609929','2024-08-19 15:53:34.609958','娱乐','','Expenses:Culture',1),(1211,'2024-08-19 15:53:34.615989','2024-08-19 15:53:34.616009','上海拉扎斯信息科技有限公司','饿了么','Expenses:Food',1),(1212,'2024-08-19 15:53:34.622319','2024-08-19 15:53:34.622343','夜宵','','Expenses:Food:Dinner',1),(1213,'2024-08-19 15:53:34.631386','2024-08-19 15:53:34.631410','打车','','Expenses:TransPort:Public',1),(1214,'2024-08-19 15:53:34.637534','2024-08-19 15:53:34.637566','抖音电商','抖音','Expenses:Shopping',1),(1215,'2024-08-19 15:53:34.643894','2024-08-19 15:53:34.643927','商城','','Expenses:Shopping',1),(1216,'2024-08-19 15:53:34.652040','2024-08-19 15:53:34.652063','保险','','Expenses:Finance:Insurance',1),(1217,'2024-08-19 15:53:34.658368','2024-08-19 15:53:34.658390','寄件','','Expenses:Home:Single',1),(1218,'2024-08-19 15:53:34.664385','2024-08-19 15:53:34.664400','书店','','Expenses:Culture',1),(1219,'2024-08-19 15:53:34.673747','2024-08-19 15:53:34.673763','外卖','','Expenses:Food',1),(1220,'2024-08-19 15:53:34.682259','2024-08-19 15:53:34.682272','滴滴出行','','Expenses:TransPort:Public',1),(1221,'2024-08-19 15:53:34.688137','2024-08-19 15:53:34.688151','公交','','Expenses:TransPort:Public',1),(1222,'2024-08-19 15:53:34.696179','2024-08-19 15:53:34.696196','航空','','Expenses:TransPort:Public',1),(1223,'2024-08-19 15:53:34.704361','2024-08-19 15:53:34.704396','储值','','Assets:Savings:Recharge',1),(1224,'2024-08-19 15:53:34.713067','2024-08-19 15:53:34.713091','出行','','Expenses:TransPort:Public',1),(1225,'2024-08-19 15:53:34.719628','2024-08-19 15:53:34.719659','下午茶','','Expenses:Food',1),(1226,'2024-08-19 15:53:34.726168','2024-08-19 15:53:34.726201','老婆','','Liabilities:Payables:Personal:WangKaiYi',1),(1227,'2024-08-19 15:53:34.732754','2024-08-19 15:53:34.732785','食物','','Expenses:Food',1),(1228,'2024-08-19 15:53:34.739862','2024-08-19 15:53:34.739894','午饭','','Expenses:Food:Lunch',1),(1229,'2024-08-19 15:53:34.747866','2024-08-19 15:53:34.747886','晚饭','','Expenses:Food:Dinner',1),(1230,'2024-08-19 15:53:34.753766','2024-08-19 15:53:34.753790','早饭','','Expenses:Food:Breakfast',1),(1231,'2024-08-19 15:53:34.763090','2024-08-19 15:53:34.763114','水费-','国家水网','Expenses:Home:Recharge',1),(1232,'2024-08-19 15:53:34.770961','2024-08-19 15:53:34.770990','电费-','国家电网','Expenses:Home:Recharge',1),(1233,'2024-08-19 15:53:34.778896','2024-08-19 15:53:34.778929','物流','','Expenses:Home',1),(1234,'2024-08-19 15:53:34.786384','2024-08-19 15:53:34.786413','快递','','Expenses:Home',1),(1235,'2024-08-19 15:53:34.795577','2024-08-19 15:53:34.795637','速递','','Expenses:Home',1),(1236,'2024-08-19 15:53:34.802351','2024-08-19 15:53:34.802399','App Store','','Expenses:Culture:Subscription',1),(1237,'2024-08-19 15:53:34.810318','2024-08-19 15:53:34.810428','饭店','','Expenses:Food',1),(1238,'2024-08-19 15:53:34.819482','2024-08-19 15:53:34.819565','面馆','','Expenses:Food',1),(1239,'2024-08-19 15:53:34.828814','2024-08-19 15:53:34.828908','服饰','','Expenses:Shopping:Clothing',1),(1240,'2024-08-19 15:53:34.836925','2024-08-19 15:53:34.837003','METRO','','Expenses:TransPort:Public',1),(1241,'2024-08-19 15:53:34.846822','2024-08-19 15:53:34.846900','食堂','','Expenses:Food',1),(1242,'2024-08-19 15:53:34.855181','2024-08-19 15:53:34.855265','生活缴费','','Expenses:Home',1),(1243,'2024-08-19 15:53:34.864656','2024-08-19 15:53:34.864730','速运','','Expenses:Home',1),(1244,'2024-08-19 15:53:34.872902','2024-08-19 15:53:34.872977','跑腿','','Expenses:Home',1),(1245,'2024-08-19 15:53:34.882697','2024-08-19 15:53:34.882791','霸王茶姬','霸王茶姬','Expenses:Food:DrinkFruit',1),(1246,'2024-08-19 15:53:34.890474','2024-08-19 15:53:34.890547','中医','','Expenses:Health',1),(1247,'2024-08-19 15:53:34.900367','2024-08-19 15:53:34.900431','理疗','','Expenses:Health',1),(1248,'2024-08-19 15:53:34.909840','2024-08-19 15:53:34.909923','肉粉馆','','Expenses:Food',1),(1249,'2024-08-19 15:53:34.918396','2024-08-19 15:53:34.918452','增值服务','','Expenses:Culture:Subscription',1),(1250,'2024-08-19 15:53:34.927763','2024-08-19 15:53:34.927826','购物','','Expenses:Shopping',1),(1251,'2024-08-19 15:53:34.934451','2024-08-19 15:53:34.934506','药业','','Expenses:Health:Medical',1),(1252,'2024-08-19 15:53:34.943370','2024-08-19 15:53:34.943435','药品','','Expenses:Health:Medical',1),(1253,'2024-08-19 15:53:34.951794','2024-08-19 15:53:34.951838','牙膏','','Expenses:Home:Daily',1),(1254,'2024-08-19 15:53:34.959932','2024-08-19 15:53:34.959994','运费','','Expenses:Home',1),(1255,'2024-08-19 15:53:34.968572','2024-08-19 15:53:34.968652','税务','','Expenses:Government',1),(1256,'2024-08-19 15:53:34.978612','2024-08-19 15:53:34.978695','充值','','Expenses:Home:Recharge',1),(1257,'2024-08-19 15:53:34.986957','2024-08-19 15:53:34.986997','订阅','','Expenses:Culture:Subscription',1),(1258,'2024-08-19 15:53:34.996751','2024-08-19 15:53:34.996840','轮胎','','Expenses:TransPort:Private',1),(1259,'2024-08-19 15:53:35.006437','2024-08-19 15:53:35.006511','服饰鞋包','','Expenses:Shopping:Clothing',1),(1260,'2024-08-19 15:53:35.014560','2024-08-19 15:53:35.014635','数码电器','','Expenses:Shopping:Digital',1),(1261,'2024-08-19 15:53:35.023706','2024-08-19 15:53:35.023776','美容美发','','Expenses:Shopping:Makeup',1),(1262,'2024-08-19 15:53:35.031168','2024-08-19 15:53:35.031226','母婴亲子','','Expenses:Shopping:Parent',1),(1263,'2024-08-19 15:53:35.037792','2024-08-19 15:53:35.037843','日用百货','','Expenses:Home:Daily',1),(1264,'2024-08-19 15:53:35.045613','2024-08-19 15:53:35.045664','门诊','','Expenses:Health',1),(1265,'2024-08-19 15:53:35.054376','2024-08-19 15:53:35.054427','挂号','','Expenses:Health',1),(1266,'2024-08-19 15:53:35.062734','2024-08-19 15:53:35.062797','体检','','Expenses:Health',1),(1267,'2024-08-19 15:53:35.070441','2024-08-19 15:53:35.070493','燃气','','Expenses:Home:Recharge',1),(1268,'2024-08-19 15:53:35.080472','2024-08-19 15:53:35.080525','装修','','Expenses:Home:Decoration',1),(1269,'2024-08-19 15:53:35.088590','2024-08-19 15:53:35.088671','科沃斯','科沃斯','Expenses:Shopping:Digital',1),(1270,'2024-08-19 15:53:35.096436','2024-08-19 15:53:35.096458','机器人','','Expenses:Shopping:Digital',1),(1271,'2024-08-19 15:53:35.105196','2024-08-19 15:53:35.105211','路由器','','Expenses:Shopping:Digital',1),(1272,'2024-08-19 15:53:35.113262','2024-08-19 15:53:35.113284','批发','','Expenses:Shopping',1),(1273,'2024-08-19 15:53:35.120668','2024-08-19 15:53:35.120690','小卖部','','Expenses:Shopping',1),(1274,'2024-08-19 15:53:35.129041','2024-08-19 15:53:35.129096','烧烤','','Expenses:Food',1),(1275,'2024-08-19 15:53:35.136600','2024-08-19 15:53:35.136650','排档','','Expenses:Food',1),(1276,'2024-08-19 15:53:35.145664','2024-08-19 15:53:35.145730','洗面奶','','Expenses:Shopping:Makeup',1),(1277,'2024-08-19 15:53:35.153407','2024-08-19 15:53:35.153461','婴儿','','Expenses:Shopping:Parent',1),(1278,'2024-08-19 15:53:35.162508','2024-08-19 15:53:35.162579','新生儿','','Expenses:Shopping:Parent',1),(1279,'2024-08-19 15:53:35.170044','2024-08-19 15:53:35.170120','宝宝','','Expenses:Shopping:Parent',1),(1280,'2024-08-19 15:53:35.179544','2024-08-19 15:53:35.179605','狂欢价','','Expenses:Shopping',1),(1281,'2024-08-19 15:53:35.186766','2024-08-19 15:53:35.186833','文具','','Expenses:Culture',1),(1282,'2024-08-19 15:53:35.193989','2024-08-19 15:53:35.194081','借出','','Assets:Receivables:Personal',1),(1283,'2024-08-19 15:53:35.203020','2024-08-19 15:53:35.203083','六贤记','六贤记','Assets:Savings:Recharge:LiuXianJi',1),(1284,'2024-08-19 15:53:35.210604','2024-08-19 15:53:35.210679','公共交通','','Expenses:TransPort:Public',1),(1285,'2024-08-19 15:53:35.219973','2024-08-19 15:53:35.220140','美团订单','美团','Expenses:Food',1);
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
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maps_income`
--

LOCK TABLES `maps_income` WRITE;
/*!40000 ALTER TABLE `maps_income` DISABLE KEYS */;
INSERT INTO `maps_income` VALUES (17,'2024-08-19 15:53:27.795792','2024-08-19 15:53:27.795845','红包',NULL,'Income:Receivables:RedPacket',1),(18,'2024-08-19 15:53:27.803419','2024-08-19 15:53:27.803472','凯义','凯义宝宝','Liabilities:Payables:Personal:WangKaiYi',1),(19,'2024-08-19 15:53:27.812051','2024-08-19 15:53:27.812095','小荷包',NULL,'Assets:Savings:Web:XiaoHeBao',1),(20,'2024-08-19 15:53:27.819598','2024-08-19 15:53:27.819642','老婆',NULL,'Liabilities:Payables:Personal:WangKaiYi',1),(21,'2024-08-19 15:53:27.828184','2024-08-19 15:53:27.828224','戴豪轩',NULL,'Assets:Savings:Web:XiaoHeBao:DaiHaoXuan',1),(22,'2024-08-19 15:53:27.835009','2024-08-19 15:53:27.835054','收钱码经营版收款',NULL,'Income:Business',1),(23,'2024-08-19 15:53:27.842406','2024-08-19 15:53:27.842483','出行账户余额提现',NULL,'Income:Sideline:DiDi',1),(24,'2024-08-19 15:53:27.851686','2024-08-19 15:53:27.851744','钟喜珍',NULL,'Liabilities:Payables:Personal:ZhongXiZhen',1);
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
INSERT INTO `socialaccount_socialaccount` VALUES (24,'github','59824968','2024-10-10 15:30:31.102628','2024-10-10 09:22:40.046770','{\"id\": 59824968, \"bio\": null, \"url\": \"https://api.github.com/users/dhr2333\", \"blog\": \"https://www.dhr2333.cn\", \"name\": \"daihaorui\", \"plan\": {\"name\": \"free\", \"space\": 976562499, \"collaborators\": 0, \"private_repos\": 10000}, \"type\": \"User\", \"email\": \"Dai_Haorui@163.com\", \"login\": \"dhr2333\", \"company\": \"Wenzhou Tingyun Technology Co., Ltd.\", \"node_id\": \"MDQ6VXNlcjU5ODI0OTY4\", \"hireable\": null, \"html_url\": \"https://github.com/dhr2333\", \"location\": \"ZheJiang WenZhou\", \"followers\": 1, \"following\": 1, \"gists_url\": \"https://api.github.com/users/dhr2333/gists{/gist_id}\", \"repos_url\": \"https://api.github.com/users/dhr2333/repos\", \"avatar_url\": \"https://avatars.githubusercontent.com/u/59824968?v=4\", \"created_at\": \"2020-01-13T10:04:59Z\", \"disk_usage\": 43348, \"events_url\": \"https://api.github.com/users/dhr2333/events{/privacy}\", \"site_admin\": false, \"updated_at\": \"2024-10-09T03:27:58Z\", \"gravatar_id\": \"\", \"starred_url\": \"https://api.github.com/users/dhr2333/starred{/owner}{/repo}\", \"public_gists\": 0, \"public_repos\": 5, \"collaborators\": 0, \"followers_url\": \"https://api.github.com/users/dhr2333/followers\", \"following_url\": \"https://api.github.com/users/dhr2333/following{/other_user}\", \"private_gists\": 1, \"twitter_username\": null, \"organizations_url\": \"https://api.github.com/users/dhr2333/orgs\", \"subscriptions_url\": \"https://api.github.com/users/dhr2333/subscriptions\", \"notification_email\": \"Dai_Haorui@163.com\", \"owned_private_repos\": 3, \"received_events_url\": \"https://api.github.com/users/dhr2333/received_events\", \"total_private_repos\": 3, \"two_factor_authentication\": true}',47),(25,'google','116230112921306348370','2024-10-11 08:03:10.707162','2024-10-10 15:31:13.226574','{\"aud\": \"27533849710-0ot3fj14f5vqkinena7is5ms08nfe2kl.apps.googleusercontent.com\", \"azp\": \"27533849710-0ot3fj14f5vqkinena7is5ms08nfe2kl.apps.googleusercontent.com\", \"exp\": 1728608590, \"iat\": 1728604990, \"iss\": \"https://accounts.google.com\", \"sub\": \"116230112921306348370\", \"name\": \"戴豪锐\", \"email\": \"a13738756428@gmail.com\", \"at_hash\": \"hmqkd2Pc_6a5gjJ2V0WTmw\", \"picture\": \"https://lh3.googleusercontent.com/a/ACg8ocKtbtXWt3nnqPDWnOfvYRJzmrimQdtrjplVVRxQfD3eQBhsq3o=s96-c\", \"given_name\": \"豪锐\", \"family_name\": \"戴\", \"email_verified\": true}',48);
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
INSERT INTO `socialaccount_socialtoken` VALUES (12,'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','',NULL,24,NULL),(13,'ya29.a0AcM612xktb0rZFwx8zdKVOe22dF8yYazpqcVzIgdy6vU2aYz3bfuexOuxENCnmKKs821QmQse-y-larvMbLLfE7cdfEn72LZQ8gpFq4RueoeSnjs7J0ke36o99a8S6kXOfvc-dtjAbO4FUWQlSS80AZDKNmgU9DhdWHCFtuWaCgYKAb8SARMSFQHGX2MisJ5M3esW0E_bIXkESfmTCw0175','','2024-10-11 09:03:09.691484',25,NULL);
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
INSERT INTO `usersessions_usersession` VALUES (34,'2024-08-29 15:57:45.974109','127.0.0.1','2024-08-29 15:57:45.973434','gh8p5di7kgfhahq0diukzvllpi2bibb0','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(37,'2024-08-29 15:59:47.858748','127.0.0.1','2024-08-29 15:59:47.858118','tupyvoz6559sczufvxsbdit7ywmnqcwz','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(38,'2024-08-29 16:01:29.536318','127.0.0.1','2024-08-29 16:01:29.532892','z11pfizzszkxc01j55nexfhmpylf08rp','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(39,'2024-08-29 16:01:59.378990','127.0.0.1','2024-08-29 16:01:59.374019','gya5i415cih151xpx7mfw33pwqpifq74','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(40,'2024-08-29 16:10:43.355034','127.0.0.1','2024-08-29 16:10:43.354290','lhkppn9ptalelz28q0uqce42h436d34r','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(41,'2024-08-29 16:31:05.148576','127.0.0.1','2024-08-29 16:31:05.146525','0o1rq32wdlr4t9rprh4fsn0eaa1lm306','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(42,'2024-08-29 17:03:42.998427','127.0.0.1','2024-08-29 17:03:42.994727','q9krlj7y9w4zh0rrjww5tao7akc20g78','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(43,'2024-08-30 08:23:56.642974','127.0.0.1','2024-08-30 08:23:56.639899','ybf2n8cc8sitmbcsyvkwfsddgcndgl0c','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(46,'2024-08-30 08:30:45.347747','127.0.0.1','2024-08-30 08:30:45.346371','gr07juq28f4bi3r4ym4dldcqti8nwyi7','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(48,'2024-08-30 13:35:02.018480','127.0.0.1','2024-08-30 13:35:23.046028','5bw4kqkp9f2ivcweg7ufcepgck5bg8qn','PostmanRuntime/7.41.2','{}',1),(49,'2024-08-30 13:35:44.877747','127.0.0.1','2024-08-30 14:22:19.319006','yuqwm6beqkxhx9302cssgf2supj0l5bu','PostmanRuntime/7.41.2','{}',1),(50,'2024-08-30 14:22:08.204512','127.0.0.1','2024-08-30 14:22:08.203541','x3pmrpkjkw680a5ujd1m4rv8owi5vacc','PostmanRuntime/7.41.2','{}',1),(51,'2024-08-30 14:22:23.994336','127.0.0.1','2024-08-30 14:22:23.993464','oy8khj0amv4wp2tbuwog5saovrg5mg75','PostmanRuntime/7.41.2','{}',1),(52,'2024-08-30 14:42:13.240521','127.0.0.1','2024-08-30 14:42:13.239770','i2h7me46efw67big60jqxy53ulggdcoq','PostmanRuntime/7.41.2','{}',1),(53,'2024-08-30 14:42:14.571535','127.0.0.1','2024-08-30 14:42:14.570877','1k3q39drwfcksbc649lr9o4mrbtpilaj','PostmanRuntime/7.41.2','{}',1),(54,'2024-08-30 14:42:15.577655','127.0.0.1','2024-08-30 14:42:15.576311','g0qtjlil3jo44itatmofll2wxuhjxcwd','PostmanRuntime/7.41.2','{}',1),(55,'2024-08-30 14:57:00.400912','127.0.0.1','2024-08-30 14:57:00.400145','svj8l8hfda62cqa9pprarxp8yzxu7w6d','PostmanRuntime/7.41.2','{}',1),(56,'2024-08-30 14:57:30.617503','127.0.0.1','2024-08-30 14:57:30.616781','gtlbmln87m9tnb0pcy3ypj2jol8kr8cv','PostmanRuntime/7.41.2','{}',1),(57,'2024-08-30 15:01:07.644455','127.0.0.1','2024-08-30 15:01:07.643743','hmxtnj7sbauhtwbon9uwciosqsa8dmq3','PostmanRuntime/7.41.2','{}',1),(58,'2024-08-30 15:01:21.271791','127.0.0.1','2024-08-30 15:01:21.270700','w0z6jfoddozjx5qjmyyihw4lq49cq555','PostmanRuntime/7.41.2','{}',1),(59,'2024-08-30 15:01:22.868027','127.0.0.1','2024-08-30 15:01:22.867330','zob3xek8yk79pvkiedkex8eg3kcnt802','PostmanRuntime/7.41.2','{}',1),(60,'2024-08-30 15:01:24.893624','127.0.0.1','2024-08-30 15:01:24.892831','rc214sk7tascw2oae198e015rachx1ja','PostmanRuntime/7.41.2','{}',1),(65,'2024-08-31 16:13:29.898428','127.0.0.1','2024-08-31 16:13:29.897595','w3slu4un5n115qwt4879oxml3irz1b0i','PostmanRuntime/7.41.2','{}',1),(66,'2024-08-31 16:14:33.468858','127.0.0.1','2024-08-31 16:14:33.468208','jhkuwlfzn3d2y11qyjtzpnu27wub7x4z','PostmanRuntime/7.41.2','{}',1),(67,'2024-08-31 16:14:34.747895','127.0.0.1','2024-08-31 16:14:34.746656','ktioqwoqq6hy0nos3mgrzh79pod1cuyx','PostmanRuntime/7.41.2','{}',1),(68,'2024-08-31 16:14:35.887614','127.0.0.1','2024-08-31 16:14:35.886967','8d88vvxsplfs84zpr7yp03rta3cdud2e','PostmanRuntime/7.41.2','{}',1),(69,'2024-08-31 16:14:37.005876','127.0.0.1','2024-08-31 16:14:37.005135','4q5fqqg2vle2zoum5tzikn9zv6dwc36y','PostmanRuntime/7.41.2','{}',1),(70,'2024-08-31 16:14:51.019279','127.0.0.1','2024-08-31 16:14:52.867000','5kunoikxmvykw2ovy00my16p8yh84y3m','PostmanRuntime/7.41.2','{}',1),(71,'2024-08-31 16:15:08.628765','127.0.0.1','2024-08-31 16:15:08.628063','f4zh07orlxo8r38k3o1r7h71lfwfl8fz','PostmanRuntime/7.41.2','{}',1),(72,'2024-08-31 16:24:27.929281','127.0.0.1','2024-08-31 16:24:27.928357','1vnrwu8wy2im9peqiv7qs1j3n1vx52mn','PostmanRuntime/7.41.2','{}',1),(73,'2024-08-31 16:24:35.696596','127.0.0.1','2024-08-31 16:24:35.695497','4ordfl9xt054m9v7qu79ogn49be5wps7','PostmanRuntime/7.41.2','{}',1),(74,'2024-08-31 16:24:36.897405','127.0.0.1','2024-08-31 16:24:36.896785','be6l8lsdvt6af8wbrq4h29e5o49ez9ma','PostmanRuntime/7.41.2','{}',1),(75,'2024-08-31 16:24:55.698146','127.0.0.1','2024-08-31 16:24:55.697447','k8hbmbewu50sw58rl70gzy3yle3cmd1r','PostmanRuntime/7.41.2','{}',1),(76,'2024-09-06 10:09:52.876578','127.0.0.1','2024-09-06 10:09:52.872715','5gpjcbafb8ad9ogxvrxofcscpknhfziq','PostmanRuntime/7.41.2','{}',1),(77,'2024-09-06 11:06:01.798346','127.0.0.1','2024-09-06 11:06:01.797304','zwi4y1np6hlf1iki85en59vutq6632qc','PostmanRuntime/7.41.2','{}',1),(78,'2024-09-06 12:57:21.182307','127.0.0.1','2024-09-06 12:57:21.181587','y3yhd5a34wpjv22ndntp78ijkgj5tqcy','PostmanRuntime/7.41.2','{}',1),(79,'2024-09-06 12:57:26.971118','127.0.0.1','2024-09-06 12:57:26.970189','f6sjw7zd54nail99gfic3oj8qck06xx8','PostmanRuntime/7.41.2','{}',1),(80,'2024-09-09 07:54:38.262183','127.0.0.1','2024-09-09 07:54:38.258310','10mu2l6wq94qrb9aovacl60x3jjnc56y','PostmanRuntime/7.41.2','{}',1),(81,'2024-09-09 07:55:34.070911','127.0.0.1','2024-09-09 07:55:34.070013','82gu2mnyytw2b757rtulryhz3vdj3lm4','PostmanRuntime/7.41.2','{}',1),(82,'2024-09-09 10:47:38.548986','127.0.0.1','2024-09-09 10:47:38.546399','da20xkha4efp685nzft15bcjussb1e8h','PostmanRuntime/7.41.2','{}',1),(83,'2024-09-09 10:48:03.120719','127.0.0.1','2024-09-09 10:48:03.119523','9pwpi3onk6nnjrzc7stxh9v1o06cwdkh','PostmanRuntime/7.41.2','{}',1),(84,'2024-09-09 10:48:09.883289','127.0.0.1','2024-09-09 10:48:09.881525','3uz5e6qxybluafkruoayzpiv8r53ryiw','PostmanRuntime/7.41.2','{}',1),(85,'2024-09-09 10:48:48.440858','127.0.0.1','2024-09-09 10:48:48.439873','4xb02ev7bnlbu2hxn8jhhrtuq1qyx5on','PostmanRuntime/7.41.2','{}',1),(86,'2024-09-09 10:49:55.300979','127.0.0.1','2024-09-09 10:49:55.299619','51lldq76a99pkoxeem0rmg4iaxqspwe0','PostmanRuntime/7.41.2','{}',1),(87,'2024-09-09 10:50:31.435691','127.0.0.1','2024-09-09 10:50:31.434507','b7du0jja2zq3ikvuyhhupr6sc4r076sy','PostmanRuntime/7.41.2','{}',1),(88,'2024-09-09 11:25:38.632761','127.0.0.1','2024-09-09 11:25:38.632099','4cwnl9c2f0o4buk0ycfi84k3htxj00q9','PostmanRuntime/7.41.2','{}',1),(89,'2024-09-10 10:28:13.915892','127.0.0.1','2024-09-10 10:28:13.913885','wxoypkwoxb39fd6oeqilb5gch4fkqu0p','PostmanRuntime/7.41.2','{}',1),(91,'2024-09-10 13:27:19.483293','127.0.0.1','2024-09-10 13:27:19.480560','b2b3pr14czyg0nfeo7h2x7r7cuakat1t','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(92,'2024-09-10 14:27:02.555422','127.0.0.1','2024-09-10 14:27:02.552684','n04sopqqqq7x5zey59otrpcomjwqol2q','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(93,'2024-09-15 12:46:03.433396','127.0.0.1','2024-09-15 12:46:03.424634','aiyw1xp7at4a8prnhea87j1fu76b84j9','PostmanRuntime/7.41.2','{}',1),(94,'2024-09-15 13:11:04.631791','127.0.0.1','2024-09-15 13:11:04.630908','m5zbir71k8e39q7dj287l6qx9qkhx6fb','PostmanRuntime/7.41.2','{}',1),(95,'2024-09-15 13:18:50.763818','127.0.0.1','2024-09-15 13:18:50.763160','6s0yn8o7fw4khxigcxzyh5sj56wit0mv','PostmanRuntime/7.41.2','{}',1),(96,'2024-09-15 13:19:16.190934','127.0.0.1','2024-09-15 13:19:16.190188','xy7vm5bgemhpvxntf0ttd0j37tgi2fck','PostmanRuntime/7.41.2','{}',1),(97,'2024-09-15 13:27:06.814908','127.0.0.1','2024-09-15 13:27:06.813620','szy4nbyr14lwrsjbe8xiplset0g3wtvd','PostmanRuntime/7.41.2','{}',1),(98,'2024-09-15 13:27:25.359538','127.0.0.1','2024-09-15 13:27:25.358458','8hlt8aldah5zbopqiq90b6zb8kkwk8j0','PostmanRuntime/7.41.2','{}',1),(99,'2024-09-15 14:01:35.718214','127.0.0.1','2024-09-15 14:01:35.717000','irevb5wjbfqvy7vtdj65uggrxhcpi9s1','PostmanRuntime/7.41.2','{}',1),(100,'2024-09-15 14:06:40.058779','127.0.0.1','2024-09-15 14:06:40.057952','8owdrj09n8rlmn9p05s02b8efk3oahvy','PostmanRuntime/7.41.2','{}',1),(101,'2024-09-15 14:07:02.043871','127.0.0.1','2024-09-15 14:07:35.874980','icab9276gah6s470l7rnj5v8moctkl0k','PostmanRuntime/7.41.2','{}',1),(102,'2024-09-15 14:07:17.792005','127.0.0.1','2024-09-15 14:07:17.791337','pagyx4qdj5udsmn1n2at36lkddzah795','PostmanRuntime/7.41.2','{}',1),(103,'2024-09-15 14:07:46.828468','127.0.0.1','2024-09-15 14:07:46.827031','22fz8twuji1lefsj3mhbttl9r5lkx882','PostmanRuntime/7.41.2','{}',1),(104,'2024-09-15 14:09:57.187209','127.0.0.1','2024-09-15 14:09:57.186043','yc0xbr7h4w3y3k63gnl50ai5pw7meh25','PostmanRuntime/7.41.2','{}',1),(105,'2024-09-15 14:16:22.693207','127.0.0.1','2024-09-15 14:16:22.691888','wsy1esdj2t1ph89h9vkp56iar0tcjis8','PostmanRuntime/7.41.2','{}',1),(106,'2024-09-15 14:48:58.406038','127.0.0.1','2024-09-15 14:48:58.405358','7f4x4jxmmbj6g34bt2z3gtkm7bkdxb9u','PostmanRuntime/7.41.2','{}',1),(107,'2024-09-15 14:49:16.287341','127.0.0.1','2024-09-15 14:49:16.286621','645bwdf9s398diaf2yhs02bbm45ql57o','PostmanRuntime/7.41.2','{}',1),(108,'2024-09-15 14:56:30.412091','127.0.0.1','2024-09-15 14:56:30.411566','u5uyzi6cx64wdx2at3wyvkz8wsvunx2v','PostmanRuntime/7.41.2','{}',1),(109,'2024-09-15 14:56:43.655204','127.0.0.1','2024-09-15 14:56:43.654477','do1vaagunkzy0aeb4ycjt9lll2ad1d5u','PostmanRuntime/7.41.2','{}',1),(110,'2024-09-15 14:58:04.737470','127.0.0.1','2024-09-15 14:58:04.736814','p7k76h5xhd7k7sstkzx91vqb5nf5112o','PostmanRuntime/7.41.2','{}',1),(111,'2024-09-15 15:49:55.210479','127.0.0.1','2024-09-15 15:49:55.209027','a1jyeegq9esqas3mj8c7yi4mwo7lbcqp','PostmanRuntime/7.41.2','{}',1),(112,'2024-09-15 15:54:10.236735','127.0.0.1','2024-09-15 15:54:10.236095','rxdlrgi317mycjrz1ryry8bh61ljmv8a','PostmanRuntime/7.41.2','{}',1),(113,'2024-09-15 15:55:15.421647','127.0.0.1','2024-09-15 15:55:15.421043','zq0r95bm485yf11qnrpxb3jpitsdr9ap','PostmanRuntime/7.41.2','{}',1),(114,'2024-09-15 16:11:11.903230','127.0.0.1','2024-09-15 16:11:11.899789','454y3vjhpginv3whe21y2bwxpy8g91ss','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(115,'2024-09-15 16:56:56.225747','127.0.0.1','2024-09-15 16:56:56.222088','zwexp5qyva0clefjwmgshqjvck9wm5y5','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(116,'2024-09-15 16:57:05.328740','127.0.0.1','2024-09-15 16:57:05.325438','yoia4o7lfmxq3ynnzue042lsf7i97bzh','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','{}',1),(117,'2024-09-25 10:35:02.815955','127.0.0.1','2024-09-25 10:35:02.813283','g2dy5m9uf67xzkbimvv90vgmzyqoafhd','PostmanRuntime/7.41.2','{}',1),(120,'2024-09-30 16:51:23.690012','127.0.0.1','2024-09-30 16:51:23.686706','8du08etc51oh9bb1lcxb5hhp86l8b3gd','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',1),(123,'2024-10-04 14:28:06.057060','127.0.0.1','2024-10-04 14:28:06.053504','n9kxjchshgpu92dyrun87j9oxqw1rc1g','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',1),(125,'2024-10-06 14:13:57.256977','127.0.0.1','2024-10-06 14:13:57.253570','czm1l4sg5dqedv044w0cbyk1c0bqth2g','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',1),(135,'2024-10-08 11:25:02.397095','127.0.0.1','2024-10-08 11:25:02.394210','spbzmly9eotrspk2lmt4hm5gsw6zavgm','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',1),(136,'2024-10-08 11:25:39.944446','127.0.0.1','2024-10-08 11:25:39.941445','67c90cof0msr5cim4nd9zsdm72o1ax40','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',1),(144,'2024-10-09 17:08:39.449781','127.0.0.1','2024-10-09 17:08:39.448713','79we0x678ngcfav9qis9jg30f9r5zu5h','PostmanRuntime/7.42.0','{}',1),(145,'2024-10-10 08:16:11.152688','127.0.0.1','2024-10-10 08:16:11.151546','e5ywqfrzlxxrz9spfadleuhrw2skr9xb','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',1),(147,'2024-10-10 09:14:36.469797','127.0.0.1','2024-10-10 09:14:36.465285','x41xk65kl85l9t5w26rcxfiwr9trz4ai','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',1),(150,'2024-10-10 09:22:40.087615','127.0.0.1','2024-10-10 09:22:40.084983','l8xt9n1zup6hq19igsugp79wtdxgowfv','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',47),(152,'2024-10-10 09:34:35.702580','127.0.0.1','2024-10-10 09:34:35.701747','x9c5idbd2jhve0d83y6gwhm77pmsq2sj','PostmanRuntime/7.42.0','{}',1),(153,'2024-10-10 09:52:27.818113','127.0.0.1','2024-10-10 09:52:27.817196','5ha7mbujps5knh7n6m84ynk83qlr2npu','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',47),(156,'2024-10-10 15:28:23.194442','127.0.0.1','2024-10-10 15:28:23.189535','dnyr67u59fcghwvbn2ent15fjrpxrrcz','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',47),(157,'2024-10-10 15:28:46.976520','127.0.0.1','2024-10-10 15:28:46.972087','e8lybfgiabs104uhksu1qe2grn4utsbi','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',1),(159,'2024-10-10 15:30:31.144651','127.0.0.1','2024-10-10 15:30:31.141325','xk432cyuahz8fjm40h43ejt2t3rvxomt','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',47),(160,'2024-10-10 15:31:13.278714','127.0.0.1','2024-10-10 15:31:13.275478','ppaqnwjn9x39m69b1smohfl0u4jzh9dp','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',48),(161,'2024-10-10 15:35:07.121461','127.0.0.1','2024-10-10 15:35:07.120475','40b6u93r43pxhdr8yx02gglq6b7dcaqc','PostmanRuntime/7.42.0','{}',1),(162,'2024-10-10 15:35:16.531035','127.0.0.1','2024-10-10 15:35:16.530330','8ck796g9zx8pv5g65kc8qkrtapmch885','PostmanRuntime/7.42.0','{}',1),(163,'2024-10-10 15:47:37.028030','127.0.0.1','2024-10-10 15:47:37.027050','3dr3ew3oh1nsvu96ciwd2xen0f57r19p','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',48),(164,'2024-10-10 15:59:13.097964','127.0.0.1','2024-10-10 15:59:13.095228','gygw5bypw5ecbeas9f97sljepxmcv4s1','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',48),(165,'2024-10-10 16:31:33.085868','127.0.0.1','2024-10-10 16:31:33.084980','rmylht5xtyzyd58pujonx31zrvz0zxbd','PostmanRuntime/7.42.0','{}',1),(166,'2024-10-11 08:03:10.755297','127.0.0.1','2024-10-11 08:03:10.750460','7hlfp8ewa9l22pl228hy8zf6g150ejlr','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36','{}',48);
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

-- Dump completed on 2024-10-12 13:30:52

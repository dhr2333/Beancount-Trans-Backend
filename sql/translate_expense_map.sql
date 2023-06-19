-- MySQL dump 10.13  Distrib 8.0.33, for Linux (x86_64)
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
-- Table structure for table `translate_expense_map`
--

DROP TABLE IF EXISTS `translate_expense_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `translate_expense_map` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `key` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `payee` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `expend` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `tag` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `classification` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `payee_order` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`)
) ENGINE=InnoDB AUTO_INCREMENT=74 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `translate_expense_map`
--

LOCK TABLES `translate_expense_map` WRITE;
/*!40000 ALTER TABLE `translate_expense_map` DISABLE KEYS */;
INSERT INTO `translate_expense_map` VALUES (1,'蜜雪冰城','蜜雪冰城','Expenses:Food:DrinkFruit','饮料水果','餐饮美食/饮料水果',100),(2,'停车','','Expenses:TransPort:Private:Park','停车费','交通出行/停车费',100),(3,'鲜花','','Expenses:Culture','文化休闲','文化休闲/文化休闲',100),(4,'古茗','古茗','Expenses:Food:DrinkFruit','饮料水果','餐饮美食/饮料水果',100),(5,'王者荣耀','腾讯','Expenses:Culture:Entertainment','影音娱乐','文化休闲/影音娱乐',100),(6,'益味坊','益味坊','Expenses:Food:Breakfast','养生早餐','餐饮美食/养生早餐',100),(7,'塔斯汀','塔斯汀','Expenses:Food:Dinner','餐饮美食','餐饮美食/餐饮美食',100),(8,'十足','十足','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(9,'一点点','一点点','Expenses:Food:DrinkFruit','饮料水果','餐饮美食/饮料水果',100),(10,'luckin','瑞幸','Expenses:Food:DrinkFruit','饮料水果','餐饮美食/饮料水果',100),(11,'娘娘大人','娘娘大人','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(12,'老婆大人','老婆大人','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(13,'高速','','Expenses:TransPort:Public','公共交通','交通出行/公共交通',100),(14,'茶百道','茶百道','Expenses:Food:DrinkFruit','饮料水果','餐饮美食/饮料水果',100),(15,'京东','京东','Expenses:Other','购物消费','购物消费/购物消费',100),(16,'连续包月','','Expenses:Culture:Subscription','影音娱乐','日常消费/影音娱乐',100),(17,'正新鸡排','正新鸡排','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(18,'药房','','Expenses:Health:Medical','医疗药品','医疗健康/医疗药品',100),(19,'药店','','Expenses:Health:Medical','医疗药品','医疗健康/医疗药品',100),(20,'医院','','Expenses:Health','医疗健康','医疗健康/医疗健康',100),(21,'餐饮','','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(22,'食品','','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(23,'腾讯天游','腾讯','Expenses:Culture:Entertainment','影音娱乐','文化休闲/影音娱乐',100),(24,'水果','','Expenses:Food:DrinkFruit','饮料水果','餐饮美食/饮料水果',100),(25,'早餐','','Expenses:Food:Breakfast','养生早餐','餐饮美食/养生早餐',100),(26,'充电','','Expenses:TransPort:Private:Fuel','燃料费','交通出行/燃料费',100),(27,'加油','','Expenses:TransPort:Private:Fuel','燃料费','交通出行/燃料费',100),(28,'ETC','','Expenses:TransPort:Public','公共交通','交通出行/公共交通',100),(29,'华为终端有限公司','华为','Expenses:Shopping:Digital','电子数码','购物消费/电子数码',100),(30,'饿了么','饿了么','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(31,'美团','美团','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(32,'地铁','','Expenses:TransPort:Public','公共交通','交通出行/公共交通',100),(33,'国网智慧车联网','国家电网','Expenses:TransPort:Private:Fuel','公共交通','交通出行/公共交通',100),(34,'肯德基','肯德基','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(35,'中国移动','中国移动','Expenses:Home:Recharge','充值缴费','居家生活/充值缴费',100),(36,'华为','华为','Expenses:Shopping:Digital','电子数码','购物消费/电子数码',100),(37,'沙县小吃','沙县小吃','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(38,'一鸣','一鸣','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(39,'之上','之上','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(40,'大疆','大疆','Expenses:Shopping:Digital','购物消费','购物消费/电子数码',100),(41,'12306','12306','Expenses:TransPort:Public','公共交通','交通出行/公共交通',100),(42,'阿里云','阿里云','Expenses:Culture:Subscription','订阅服务','文化休闲/订阅服务',100),(43,'电影','','Expenses:Culture:Entertainment','影音娱乐','文化休闲/影音娱乐',100),(44,'火车','12306','Expenses:TransPort:Public','公共交通','交通出行/公共交通',100),(45,'高铁','12306','Expenses:TransPort:Public','公共交通','交通出行/公共交通',100),(46,'飞机','12306','Expenses:TransPort:Public','公共交通','交通出行/公共交通',100),(47,'医疗','','Expenses:Health','医疗健康','医疗健康/医疗健康',100),(48,'医生','','Expenses:Health','医疗健康','医疗健康/医疗健康',100),(49,'医用','','Expenses:Health','医疗健康','医疗健康/医疗健康',100),(50,'小吃','','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(51,'餐厅','','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(52,'**','淘宝','Expenses:Shopping','购物消费','购物消费/购物消费',100),(53,'小食','','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(54,'旗舰店','淘宝','Expenses:Shopping','购物消费','购物消费/购物消费',100),(55,'粮粮驾到','粮粮驾到','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(56,'中国石油','中国石油','Expenses:TransPort:Private:Fuel','燃料费','交通出行/燃料费',100),(57,'酒店','','Expenses:Culture','文化休闲','文化休闲/文化休闲',100),(58,'KFC','肯德基','Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(59,'高德','高德','Expenses:TransPort:Public','公共交通','交通出行/公共交通',100),(60,'饭',NULL,'Expenses:Food','餐饮美食','餐饮美食/餐饮美食',100),(61,'烟酒',NULL,'Expenses:Food:DrinkFruit','餐饮美食','餐饮美食/饮料水果',100),(62,'理发',NULL,'Expenses:Shopping:Makeup','购物消费','购物消费/美容美发',100),(63,'美发',NULL,'Expenses:Shopping:Makeup','购物消费','购物消费/美容美发',100),(64,'美容',NULL,'Expenses:Shopping:Makeup','购物消费','购物消费/美容美发',100);
/*!40000 ALTER TABLE `translate_expense_map` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-06-19 13:46:45

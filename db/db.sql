--
-- Table structure for table `user`
--

-- CREATE DATABASE chess;
-- USE chess
-- CREATE USER 'chess'@'localhost' IDENTIFIED BY 'thepassword';
-- GRANT ALL ON chess.* TO 'chess'@'localhost';
SET time_zone='+00:00';

DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `user_id` int(8) NOT NULL AUTO_INCREMENT,
  `user_name` varchar(17) NOT NULL,
  `user_passwd` char(64) DEFAULT NULL,
  `user_real_name` varchar(64) NOT NULL,
  `user_email` varchar(32) NOT NULL,
  `user_admin_level` smallint(4) unsigned NOT NULL,
  `user_fics_name` varchar(18) DEFAULT NULL,
  `user_first_login` timestamp NULL DEFAULT NULL,
  `user_last_logout` timestamp NULL DEFAULT NULL,
  `user_total_time_online` int(8) unsigned NOT NULL DEFAULT 0,
  `user_banned` BOOLEAN NOT NULL DEFAULT 0,
  `user_muzzled` BOOLEAN NOT NULL DEFAULT 0,
  `user_cmuzzled` BOOLEAN NOT NULL DEFAULT 0,
  `user_muted` BOOLEAN NOT NULL DEFAULT 0,
  `user_notebanned` BOOLEAN NOT NULL DEFAULT 0,
  `user_ratedbanned` BOOLEAN NOT NULL DEFAULT 0,
  `user_playbanned` BOOLEAN NOT NULL DEFAULT 0,

  -- vars
  `time` SMALLINT(4) NOT NULL DEFAULT 2 COMMENT 'default seek time',
  `private` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'private games',
  `shout` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'see shouts',
  `pin` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'notify whenever someone logs on or off',
  `style` SMALLINT(4) NOT NULL DEFAULT 1 COMMENT 'board style',
  `inc` SMALLINT(4) NOT NULL DEFAULT 12 COMMENT 'default increment',
  `jprivate` SMALLINT(4) NOT NULL DEFAULT 0 COMMENT 'private journal',
  `cshout` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'see c-shouts',
  `notifiedby` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'notify when others are notified',
  -- `rated` OBSOLETE
  `kibitz` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'show kibitzes',
  -- `availinfo`
  `highlight` SMALLINT(4) NOT NULL DEFAULT 0 COMMENT 'terminal highlight style',
  `open` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'open to match requests',
  `automail` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'email all games to player',
  -- `availmin` SMALLINT(4) NOT NULL DEFAULT 0,
  `bell` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'beep on board updates',
  -- `pgn` BOOLEAN NOT NULL DEFAULT 1,
  `tell` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'show tells from guests',
  -- `availmax` SMALLINT(4) NOT NULL DEFAULT 0,
  `width` SMALLINT(4) NOT NULL DEFAULT 79 COMMENT 'terminal width in characters',
  `bugopen` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'open for bughouse',
  `ctell` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'show channel tells from guests',
  `gin` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'notify when games start and end',
  `height` SMALLINT(4) NOT NULL DEFAULT 24 COMMENT 'terminal height in characters',
  `mailmess` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'email a copy of messages',
  `seek` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'show seeks',
  `ptime` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'show time in prompt',
  -- not persistent in original FICS
  -- `tourney` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'currently in a tourney',
  -- `flip` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'flip board',
  `messreply` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'send email address in mailed messages',
  `chanoff` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'hide all channel tells',
  `showownseek` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'show own seeks',
  `tzone` varchar(32) NOT NULL DEFAULT 'UTC' COMMENT 'time zone',
  `provshow` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'show provisional ratings',
  `silence` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'hide shouts and tells while playing',
  `autoflag` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'automatically flag opp',
  `unobserve` TINYINT NOT NULL DEFAULT 0 COMMENT 'automatically unobserve games',
  -- `echo` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'receive a copy of own communications',
  `examine` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'automatically examine after a game',
  `minmovetime` BOOLEAN NOT NULL DEFAULT 1 COMMENT 'use minimum move time in games',
  -- `tolerance`
  `noescape` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'agree to forfeit on disconnect',
  `notakeback` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'automatically reject takeback requests',
  `hideinfo` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'admins only: hide private user info',

  -- other flags
  `simopen` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'open for simul',
  `lang` VARCHAR(6) NOT NULL DEFAULT 'en' COMMENT 'user language',
  `country` CHAR(2) DEFAULT NULL,
  `prompt` VARCHAR(16) NOT NULL DEFAULT 'fics% ' COMMENT 'command prompt',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_name` (`user_name`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `user_log`;
CREATE TABLE `user_log` (
  `log_who_name` varchar(17) NOT NULL,
  `log_when` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `log_which` enum('login', 'logout', 'registration') NOT NULL,
  `log_ip` varchar(57) NOT NULL,
  KEY (`log_who_name`),
  KEY (`log_when`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

-- TODO: make a comlumn in user instead
DROP TABLE IF EXISTS `removed_user`;
CREATE TABLE `removed_user` LIKE `user`;

DROP TABLE IF EXISTS `formula`;
CREATE TABLE `formula` (
  `formula_id` int(8) NOT NULL AUTO_INCREMENT,
  `user_id` int(8) NOT NULL,
  `num` tinyint(1) NOT NULL COMMENT 'the variable number; formula=0, f1=1',
  `f` VARCHAR(1024) NOT NULL COMMENT 'formula text',
  UNIQUE KEY (`user_id`, `num`),
  PRIMARY KEY (`formula_id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


-- finger notes
DROP TABLE IF EXISTS `note`;
CREATE TABLE `note` (
  `note_id` int(8) NOT NULL AUTO_INCREMENT,
  `user_id` int(8) NOT NULL,
  `num` tinyint(1) NOT NULL COMMENT 'note number',
  `txt` VARCHAR(1024) NOT NULL COMMENT 'note text',
  UNIQUE KEY (`user_id`, `num`),
  PRIMARY KEY (`note_id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `channel`;
CREATE TABLE `channel` (
  -- Making channel_id AUTO_INCREMENT caused a bug with channel 0, because
  -- MySQL intepreted 0 as an auto-increment value.  Fortunately, there
  -- is no need to use AUTO_INCREMENT with channels.
  `channel_id` int(11) NOT NULL,
  `name` varchar(32) DEFAULT NULL COMMENT 'brief channel name',
  `descr` varchar(255) DEFAULT NULL COMMENT 'long channel desciption',
  `topic` varchar(1024) DEFAULT NULL COMMENT 'topic text, if any',
  `topic_who` int(8) DEFAULT NULL COMMENT 'who posted the topic',
  `topic_when` timestamp COMMENT 'when the topic was posted',
  UNIQUE KEY(`name`),
  PRIMARY KEY (`channel_id`)
) ENGINE=MyISAM AUTO_INCREMENT=0 DEFAULT CHARSET=utf8;

-- Stores which users are in which channels.
DROP TABLE IF EXISTS `channel_user`;
CREATE TABLE `channel_user` (
  `channel_id` int(8) NOT NULL,
  `user_id` int(8) NOT NULL,
  `is_owner` BOOLEAN NOT NULL DEFAULT 0,
  KEY (`channel_id`),
  KEY (`user_id`),
  UNIQUE KEY (`user_id`,`channel_id`)
) ENGINE=MyISAM;

-- titles for users, like (GM), (*), or (TM)
DROP TABLE IF EXISTS `title`;
CREATE TABLE `title` (
  `title_id` int(8) NOT NULL AUTO_INCREMENT,
  `title_name` varchar(32) COMMENT 'the corresponding list name' NOT NULL,
  `title_descr` varchar(48) NOT NULL COMMENT 'a human-readable description' NOT NULL,
  `title_flag` varchar(3) COMMENT 'e.g. * for admins or TM for tourney manager',
  `title_public` BOOLEAN COMMENT 'non-admins allowed to show the list',
  PRIMARY KEY (`title_id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `user_title`;
CREATE TABLE `user_title` (
  `user_id` int(8) NOT NULL,
  `title_id` int(8) NOT NULL,
  `title_light` BOOLEAN DEFAULT 1 COMMENT 'admin light, tm light, etc.',
  INDEX(`user_id`),
  UNIQUE INDEX(`user_id`,`title_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- history
-- each registered player has a game history, numbered 0 to 99
DROP TABLE IF EXISTS `history`;
CREATE TABLE `history` (
  `user_id` int(8) NOT NULL,
  `num` tinyint(2) NOT NULL COMMENT 'history number 0-99',
  `game_id` int(8) NOT NULL,
  `guest_opp_name` VARCHAR(17) COMMENT 'opponent name if a guest',
  INDEX(`user_id`),
  UNIQUE INDEX(`user_id`, `num`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- IP address filter for guests
DROP TABLE IF EXISTS `ip_filter`;
CREATE TABLE `ip_filter` (
  `filter_id` int(8) NOT NULL AUTO_INCREMENT,
  `filter_pattern` VARCHAR(61) NOT NULL,
  PRIMARY KEY (`filter_id`),
  UNIQUE KEY (`filter_pattern`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- gateways trusted to set a different IP
DROP TABLE IF EXISTS `ip_gateway`;
CREATE TABLE `ip_gateway` (
  `gateway_id` int(4) NOT NULL AUTO_INCREMENT,
  `ip` VARCHAR(61) NOT NULL,
  PRIMARY KEY (`gateway_id`),
  UNIQUE KEY (`ip`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- game
-- This table could be very large.
-- TODO: store overtime_move_num and overtime_bonus in a separate table?
DROP TABLE IF EXISTS `game`;
CREATE TABLE `game` (
  `game_id` int(8) NOT NULL AUTO_INCREMENT,
  `white_user_id` INT(8) COMMENT 'ID of the white player or NULL for guest',
  `black_user_id` INT(8) COMMENT 'ID of the black player or NULL for guest',
  `white_rating` char(4) NOT NULL COMMENT '0 for no rating', -- TODO: use smallint instead
  `black_rating` char(4) NOT NULL COMMENT '0 for no rating',
  `eco` char(5) NOT NULL,
  `speed_id` TINYINT NOT NULL,
  `variant_id` TINYINT NOT NULL,
  `clock_id` int(4) NOT NULL,
  -- `private` BOOLEAN NOT NULL DEFAULT 0,
  `time` int(3) COMMENT 'initial time',
  `inc` int(3) COMMENT 'increment',
  `is_rated` BOOLEAN NOT NULL COMMENT 'is the game rated?',
  `ply_count` SMALLINT NOT NULL COMMENT 'number of half-moves in the game',
  `movetext` TEXT,
  `when_started` TIMESTAMP NOT NULL,
  `when_ended` TIMESTAMP NOT NULL
    COMMENT 'when the game was finished or adjourned',
  `is_adjourned` BOOLEAN COMMENT 'is this an adjourned game?',

  -- for games with overtime-style clocks only
  `overtime_move_num` INT(4) DEFAULT NULL COMMENT 'time control for overtime clocks',
  `overtime_bonus` INT(4) DEFAULT NULL COMMENT 'minutes added at time control for overtime clocks',

  -- for completed games only
  `result` ENUM('1-0', '0-1', '1/2-1/2', '*') DEFAULT NULL,
  `result_reason` ENUM('Adj', 'Agr', 'Dis', 'Fla', 'Mat', 'NM', 'Sta',
     'StB', 'Rep', 'Res', 'TM', 'PW', 'PDr', 'WLM', 'WNM', 'MBB',
     '50') DEFAULT NULL,

  -- for adjourned games only
  `white_clock` float DEFAULT NULL,
  `black_clock` float DEFAULT NULL,
  `adjourn_reason` ENUM('Agr', 'Dis') DEFAULT NULL,
  `white_material` TINYINT DEFAULT NULL,
  `black_material` TINYINT DEFAULT NULL,
  `draw_offered` BOOLEAN DEFAULT NULL,

  INDEX(`white_user_id`),
  INDEX(`black_user_id`),
  INDEX(`when_ended`),
  PRIMARY KEY (`game_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `clock`;
CREATE TABLE `clock` (
  `clock_id` int(8) NOT NULL AUTO_INCREMENT,
  `clock_name` varchar(16) NOT NULL,
  PRIMARY KEY (`clock_id`),
  KEY(`clock_name`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- ECO codes
-- use import-eco.py to populate
DROP TABLE IF EXISTS `eco`;
CREATE TABLE `eco` (
  `eco_id` int(4) NOT NULL AUTO_INCREMENT,
  `eco` char(5) NOT NULL,
  `long_` varchar(128) NOT NULL,
  `hash` bigint(12) UNSIGNED NOT NULL UNIQUE,
  `fen` varchar(88) NOT NULL UNIQUE COLLATE utf8_bin,
  PRIMARY KEY (`eco_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- NIC codes
DROP TABLE IF EXISTS `nic`;
CREATE TABLE `nic` (
  `nic_id` int(4) NOT NULL AUTO_INCREMENT,
  `nic` char(5) NOT NULL,
  `hash` bigint(12) UNSIGNED NOT NULL UNIQUE,
  `fen` varchar(88) NOT NULL UNIQUE COLLATE utf8_bin,
  PRIMARY KEY (`nic_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- notifications of arrival and departure
DROP TABLE IF EXISTS `user_notify`;
CREATE TABLE `user_notify` (
  `notified` int(8) NOT NULL COMMENT 'id of the user receiving the notification',
  `notifier` int(8) NOT NULL COMMENT 'id of the user causing the notification',
  UNIQUE INDEX(`notified`, `notifier`)
);

-- TODO: combine with user_notify
-- game notifications
DROP TABLE IF EXISTS `user_gnotify`;
CREATE TABLE `user_gnotify` (
  `gnotified` int(8) NOT NULL COMMENT 'id of the user receiving the notification',
  `gnotifier` int(8) NOT NULL COMMENT 'id of the user causing the notification',
  UNIQUE INDEX(`gnotified`, `gnotifier`)
);

-- censor lists
DROP TABLE IF EXISTS `censor`;
CREATE TABLE `censor` (
  `censorer` int(8) NOT NULL COMMENT 'id of the censoring user',
  `censored` int(8) NOT NULL COMMENT 'id of the user being censored',
  UNIQUE INDEX(`censorer`, `censored`)
);

-- noplay lists
DROP TABLE IF EXISTS `noplay`;
CREATE TABLE `noplay` (
  `noplayer` int(8) NOT NULL COMMENT 'id of the noplaying user',
  `noplayed` int(8) NOT NULL COMMENT 'id of the user being noplayed',
  UNIQUE INDEX(`noplayer`, `noplayed`)
);

-- user aliases
DROP TABLE IF EXISTS `user_alias`;
CREATE TABLE user_alias (
  `alias_id` int(8) NOT NULL AUTO_INCREMENT,
  `user_id` int(8) NOT NULL,
  `name` VARCHAR(16) NOT NULL COMMENT 'alias word',
  `val` VARCHAR(1024) NOT NULL COMMENT 'alias value',
  UNIQUE KEY (`user_id`, `name`),
  PRIMARY KEY (`alias_id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

-- speed
-- lightning, blitz, etc.
DROP TABLE IF EXISTS `speed`;
CREATE TABLE `speed` (
  `speed_id` int(8) NOT NULL AUTO_INCREMENT,
  `speed_name` varchar(16) NOT NULL,
  `speed_abbrev` char(2) NOT NULL,
  PRIMARY KEY(`speed_id`)
);

-- variant
-- chess, crazyhouse, etc.
DROP TABLE IF EXISTS `variant`;
CREATE TABLE `variant` (
  `variant_id` int(8) NOT NULL AUTO_INCREMENT,
  `variant_name` varchar(16) NOT NULL,
  `variant_abbrev` char(2) NOT NULL,
  PRIMARY KEY(`variant_id`)
);
-- ratings
DROP TABLE IF EXISTS `rating`;
CREATE TABLE `rating` (
  `rating_id` int(8) NOT NULL AUTO_INCREMENT, -- is this necessary?
  `user_id` int(8) NOT NULL,
  `variant_id` int(8) NOT NULL,
  `speed_id` int(8) NOT NULL,
  `rating` smallint(4) NOT NULL,
  `rd` float NOT NULL,
  `volatility` float NOT NULL,
  `win` int(7) NOT NULL,
  `loss` int(7) NOT NULL,
  `draw` int(7) NOT NULL,
  `total` int(7) NOT NULL COMMENT 'equals win + loss + draw, but included for efficiency',
  `best` int(4) COMMENT 'best active rating',
  `when_best` date COMMENT 'when best rating was achieved',
  `ltime` timestamp NOT NULL DEFAULT 0 COMMENT 'when RD was last updated',
  UNIQUE KEY (`user_id`, `variant_id`, `speed_id`),
  INDEX(`user_id`),
  PRIMARY KEY(`rating_id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

-- news
DROP TABLE IF EXISTS `news_index`;
CREATE TABLE `news_index` (
  `news_id` int(4) NOT NULL AUTO_INCREMENT,
  `news_title` VARCHAR(45) NOT NULL,
  `news_when` TIMESTAMP NOT NULL COMMENT 'when posted',
  `news_poster` VARCHAR(17) NOT NULL,
  `news_is_admin` BOOLEAN NOT NULL COMMENT 'normal or admin news item',
  PRIMARY KEY(`news_id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `news_line`;
CREATE TABLE `news_line` (
  `news_id` int(8) NOT NULL,
  `num` tinyint UNSIGNED NOT NULL DEFAULT 1 COMMENT 'line number',
  `txt` VARCHAR(1023) NOT NULL COMMENT 'news line text',
  UNIQUE KEY(`news_id`,`num`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- messages
DROP TABLE IF EXISTS `message`;
CREATE TABLE `message` (
  `message_id` int(8) NOT NULL AUTO_INCREMENT,
  `from_user_id` int(8) NOT NULL COMMENT 'sender ID',
  `forwarder_user_id` int(8) DEFAULT NULL,
  `to_user_id` int(8) NOT NULL COMMENT 'receiver ID',
  `num` smallint(2) NOT NULL COMMENT 'number of message for receiver',
  `txt` VARCHAR(1023) NOT NULL COMMENT 'full text of message',
  `when_sent` TIMESTAMP NOT NULL,
  `unread` BOOLEAN NOT NULL DEFAULT 1,
  KEY(`to_user_id`),
  KEY(`from_user_id`,`to_user_id`),
  KEY(`to_user_id`,`num`), -- UNIQUEness violated when renumbering
  PRIMARY KEY(`message_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `chess960_pos`;
CREATE TABLE `chess960_pos` (
  `idn` INT(4) NOT NULL,
  `fen` VARCHAR(88) NOT NULL,
  PRIMARY KEY(`idn`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- for chess960
-- stores the starting position of a game, represented by a number
-- 0-959
DROP TABLE IF EXISTS `game_idn`;
CREATE TABLE `game_idn` (
  `game_id` int(8) NOT NULL,
  `idn` INT(4) NOT NULL,
  UNIQUE KEY(`game_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- comments
DROP TABLE IF EXISTS `user_comment`;
CREATE TABLE `user_comment` (
  `comment_id` int(8) NOT NULL AUTO_INCREMENT,
  `admin_id` int(8) NOT NULL,
  `user_id` int(8) NOT NULL,
  `txt` VARCHAR(1023) NOT NULL COMMENT 'full text of comment',
  `when_added` TIMESTAMP NOT NULL,
  PRIMARY KEY(`comment_id`),
  INDEX(`user_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `server_message`;
CREATE TABLE `server_message` (
  `server_message_id` int(4) NOT NULL AUTO_INCREMENT,
  `server_message_name` VARCHAR(32) NOT NULL,
  `server_message_text` TEXT NOT NULL,
  PRIMARY KEY (`server_message_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- data
LOCK TABLES `channel` WRITE;
INSERT INTO `channel` VALUES (0,'admin','Admins only',NULL,NULL,NULL);
INSERT INTO `channel` VALUES (1,'help','Help for new (and not-so-new) users. :-)','This is the help channel.  You can get help by asking a question here; use "tell 1 My question is...".',1,NULL);
UNLOCK TABLES;

LOCK TABLES `title` WRITE;
INSERT INTO `title` VALUES (NULL,'admin','Administrator','*',1);
INSERT INTO `title` VALUES (NULL,'SR','Service Representative','SR',1);
INSERT INTO `title` VALUES (NULL,'TD','Technical Device','TD',1);
INSERT INTO `title` VALUES (NULL,'TM','Tournament Manager','TM',1);
INSERT INTO `title` VALUES (NULL,'CA','Chess Advisor','CA',1);
INSERT INTO `title` VALUES (NULL,'abuser','Abuser',NULL,0);
INSERT INTO `title` VALUES (NULL,'GM','Grandmaster','GM',1);
INSERT INTO `title` VALUES (NULL,'IM','International Master','IM',1);
INSERT INTO `title` VALUES (NULL,'FM','FIDE Master','FM',1);
INSERT INTO `title` VALUES (NULL,'CM','Candidate Master','CM',1);
INSERT INTO `title` VALUES (NULL,'WGM','Woman Grandmaster','WGM',1);
INSERT INTO `title` VALUES (NULL,'WIM','Woman International Master','WIM',1);
INSERT INTO `title` VALUES (NULL,'WFM','Woman FIDE Master','WFM',1);
INSERT INTO `title` VALUES (NULL,'WCM','Woman Candidate Master','WCM',1);
INSERT INTO `title` VALUES (NULL,'blind','Blind','B',1);
INSERT INTO `title` VALUES (NULL,'computer','Computer','C',1);
UNLOCK TABLES;

LOCK TABLES `user_title` WRITE;
INSERT INTO `user_title` VALUES (1,1,1);
UNLOCK TABLES;

LOCK TABLES `speed` WRITE;
INSERT INTO `speed` VALUES (NULL,'untimed','?');
INSERT INTO `speed` VALUES (NULL,'lightning','l');
INSERT INTO `speed` VALUES (NULL,'blitz','b');
INSERT INTO `speed` VALUES (NULL,'standard','s');
INSERT INTO `speed` VALUES (NULL,'slow','o');
INSERT INTO `speed` VALUES (NULL,'corr','c');
UNLOCK TABLES;

LOCK TABLES `variant` WRITE;
INSERT INTO `variant` VALUES (NULL,'chess','n');
INSERT INTO `variant` VALUES (NULL,'crazyhouse','z');
INSERT INTO `variant` VALUES (NULL,'chess960','9');
INSERT INTO `variant` VALUES (NULL,'bughouse','B');
INSERT INTO `variant` VALUES (NULL,'suicide','S');
UNLOCK TABLES;

LOCK TABLES `server_message` WRITE;
INSERT INTO `server_message` VALUES (NULL,'motd',"Welcome to the fatics.org test server.  Message wmahan with any comments.\n\nThere is just one rule here: be nice.\n\nFor real chess, go to freechess.org instead.  Thanks for testing!\n\n");
INSERT INTO `server_message` VALUES (NULL,'welcome',"Welcome to / Bienvenue à / Bienvenido a / Willkommen auf\n\n                   ♙♘♗♖♕♔ FatICS ♚♛♜♝♞♟\n\n");
INSERT INTO `server_message` VALUES (NULL,'login',"If you are not a registered player, enter the login name \"guest\".\n\n");
INSERT INTO `server_message` VALUES (NULL,'logout',"♙♙♙ Thank you for using FatICS. ♟♟♟\n");
INSERT INTO `server_message` VALUES (NULL,'full',"Sorry, the server has reached its limit for players logged on at once.\nPlease come back later.\n");
INSERT INTO `server_message` VALUES (NULL,'full_unreg',"Sorry, the server has reached its limit for guests logged on at once.\nPlease log on using a registered account or come back later.\n");
UNLOCK TABLES;

LOCK TABLES `clock` WRITE;
INSERT INTO `clock` VALUES(NULL, 'fischer');
INSERT INTO `clock` VALUES(NULL, 'bronstein');
INSERT INTO `clock` VALUES(NULL, 'hourglass');
INSERT INTO `clock` VALUES(NULL, 'overtime');  # traditional FIDE-style
INSERT INTO `clock` VALUES(NULL, 'untimed');
UNLOCK TABLES;

SOURCE db/chess960.sql


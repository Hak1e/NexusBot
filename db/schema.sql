DROP TABLE IF EXISTS guild_settings;
DROP TABLE IF EXISTS text_channels;
DROP TABLE IF EXISTS cooldown;
DROP TABLE IF EXISTS custom_voice;
DROP TABLE IF EXISTS tournament_blacklist;
DROP TABLE IF EXISTS journal;
-- DROP TABLE IF EXISTS penalties;


CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    tickets_category_id BIGINT,
    voice_channel_category_id BIGINT,
    channel_creator_id BIGINT
);

CREATE TABLE IF NOT EXISTS text_channels (
    guild_id BIGINT PRIMARY KEY,
    art_channel_id BIGINT,
    meme_channel_id BIGINT,
    roles_id_to_mention BIGINT[],
    goodbye_channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS emoji_reactions (
    guild_id BIGINT PRIMARY KEY,
    _like TEXT,
    _dislike TEXT
);

CREATE TABLE IF NOT EXISTS cooldown (
    guild_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    button_cooldown INT,
    button_cooldown_end_time TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS custom_voice (
    guild_id BIGINT,
    user_id BIGINT,
    channel_id BIGINT,
    channel_name TEXT,
    bitrate INT,
    user_limit INT,
    channel_overwrites JSON,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS tournament_blacklist (
    guild_id BIGINT,
    user_id BIGINT,
    reason TEXT,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS journal (
    guild_id BIGINT,
    user_id BIGINT,
    notes TEXT[],
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS journal_logs (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS roles (
    role_id BIGINT PRIMARY KEY,
    guild_id BIGINT,
    name TEXT
);

CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    role_id BIGINT REFERENCES roles(role_id)
);

CREATE TABLE IF NOT EXISTS voice_creators (
    guild_id BIGINT,
    channel_creator_id BIGINT,
    user_limit INT,
    category_id BIGINT,
    PRIMARY KEY (guild_id, channel_creator_id)
);

CREATE TABLE IF NOT EXISTS created_lobbies_category_id (
    guild_id BIGINT PRIMARY KEY,
    category_id BIGINT
);

drop table created_lobbies_category_id;

CREATE TABLE IF NOT EXISTS bot_author (
    num SERIAL PRIMARY KEY,
    user_id BIGINT
);

insert into bot_author (user_id) values (389787190986670082);

CREATE TABLE IF NOT EXISTS error_logs_channel (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS rank_roles (
    guild_id BIGINT,
    role_id BIGINT,
    role_name TEXT,
    PRIMARY KEY (guild_id, role_id)
);

CREATE TABLE IF NOT EXISTS rating_lobby_text_channel_id (
    guild_id BIGINT PRIMARY KEY,
    text_channel_id BIGINT
);
alter table rating_lobby_text_channel_id owner to zorg;

CREATE TABLE IF NOT EXISTS lobby_messages (
    guild_id BIGINT,
    message_id BIGINT,
    voice_channel_id BIGINT,
    PRIMARY KEY (guild_id, message_id)
);




INSERT INTO rank_roles VALUES
(642852514865217578, 704272473067356160, 'Бронза'),
(642852514865217578, 704272430843297833, 'Серебро'),
(642852514865217578, 704272392951824474, 'Золото'),
(642852514865217578, 704272344222531585, 'Платина'),
(642852514865217578, 704272143567028225, 'Алмаз'),
(642852514865217578, 704272083676561450, 'Мастер'),
(642852514865217578, 711462625430732822, 'Элита');


INSERT INTO rank_roles VALUES
(754063467610374224, 830005257466544159, 'Бронза'),
(754063467610374224, 830005229410975785, 'Серебро'),
(754063467610374224, 830005200332914719, 'Золото'),
(754063467610374224, 830005162289528862, 'Платина'),
(754063467610374224, 830005130195369984, 'Алмаз'),
(754063467610374224, 830005094895583263, 'Легенда');



INSERT INTO voice_creators VALUES
(1129063388018921532, 1205486819714535444, 3, 1205472700496355348),
(1129063388018921532, 1205472779210727534, 5, 1205472700496355348),
(1129063388018921532, 1205472801142734858, 10, 1205472700496355348);




CREATE TABLE IF NOT EXISTS tickets (
    guild_id BIGINT PRIMARY KEY,
    button_cooldown INT,
    tickets_category_id BIGINT,
    closed_tickets_category_id BIGINT,
    question_roles_ids BIGINT[],
    report_roles_ids BIGINT[],
    offer_roles_ids BIGINT[],
    logs_channel_id BIGINT,
    total_created_tickets_number INT DEFAULT 0
);

update tickets set total_created_tickets_number = 0 where guild_id=642852514865217578;
CREATE TABLE IF NOT EXISTS ticket_users_button_cooldown (
    guild_id BIGINT,
    user_id BIGINT,
    button_cooldown_end_time TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS ticket_buttons_emojis (
    guild_id BIGINT PRIMARY KEY,
    question_button_emoji TEXT,
    report_button_emoji TEXT,
    offer_button_emoji TEXT,
    close_button_emoji TEXT,
    delete_button_emoji TEXT
);









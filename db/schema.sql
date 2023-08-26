DROP TABLE IF EXISTS guild_settings;
DROP TABLE IF EXISTS text_channels;
DROP TABLE IF EXISTS cooldown;
DROP TABLE IF EXISTS custom_voice;
DROP TABLE IF EXISTS tournament_blacklist;
DROP TABLE IF EXISTS journal;
DROP TABLE IF EXISTS penalties;


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
    roles_id_to_mention BIGINT[]
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
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS tournament_blacklist (
    guild_id BIGINT,
    user_id BIGINT,
    reason TEXT,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS bot_blacklist (
    user_id BIGINT PRIMARY KEY,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS journal (
    user_id BIGINT,
    guild_id BIGINT,
    notes TEXT[],
    PRIMARY KEY (user_id, guild_id)
);

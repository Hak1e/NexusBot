DROP TABLE IF EXISTS guild_settings;
DROP TABLE IF EXISTS cooldowns;
DROP TABLE IF EXISTS custom_voice;


CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    art_channel_id BIGINT,
    meme_channel_id BIGINT,

    tickets_category_id BIGINT,
    roles_id_to_mention BIGINT[],

    voice_channel_category_id BIGINT,
    create_voice_channel_id BIGINT,
    created_voice_channel_ids BIGINT[],

    button_cooldown INT

);

CREATE TABLE IF NOT EXISTS cooldowns (
    guild_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    button_cooldown_end_time TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS custom_voice (
    guild_id_user_id TEXT PRIMARY KEY,
    channel_name TEXT
);


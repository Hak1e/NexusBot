DROP TABLE IF EXISTS guild_settings;
DROP TABLE IF EXISTS cooldowns;


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
    user_id BIGINT PRIMARY KEY,
    button_cooldown_end_time TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS custom_voice (
    channel_creator_id BIGINT PRIMARY KEY,
    channel_name TEXT,
    permissions JSONB
);


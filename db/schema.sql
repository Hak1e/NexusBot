DROP TABLE IF EXISTS guild_settings;

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    art_channel_id BIGINT,
    meme_channel_id BIGINT,
    temp_voice_channel_category_id BIGINT,
    temp_create_voice_channel BIGINT

);

alter table guild_settings
    add temp_voice_channel_id BIGINT[];



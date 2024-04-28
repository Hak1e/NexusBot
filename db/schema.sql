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

CREATE TABLE IF NOT EXISTS bot_author (
    num SERIAL PRIMARY KEY,
    user_id BIGINT
);

insert into bot_author (user_id) values (389787190986670082);

CREATE TABLE IF NOT EXISTS error_logs_channel (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT
);

-- region Lobbies
alter table voice_creators rename to lobby_voice_creators;
alter table category_rank_roles rename to lobby_category_rank_roles;
alter table rating_lobby_text_channel_id rename to lobby_text_channel_ids;
alter table created_lobbies_category_id rename to lobby_created_voice_channels_ids;

CREATE TABLE IF NOT EXISTS lobby_voice_creators (
    guild_id BIGINT,
    channel_creator_id BIGINT,
    user_limit INT,
    category_id BIGINT,
    PRIMARY KEY (guild_id, channel_creator_id)
);

drop table lobby_category_rank_roles;
CREATE TABLE IF NOT EXISTS lobby_category_rank_roles (
    guild_id BIGINT,
    category_id BIGINT,
    role_id BIGINT,
    role_name TEXT,
    role_needed BOOL DEFAULT FALSE,
    PRIMARY KEY (guild_id, category_id, role_id)
);
alter table lobby_category_rank_roles add role_needed BOOL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS lobby_text_channel_ids (
    guild_id BIGINT,
    lobby_category_id BIGINT,
    text_channel_id BIGINT,
    PRIMARY KEY (guild_id, lobby_category_id)
);

CREATE TABLE IF NOT EXISTS lobby_messages (
    guild_id BIGINT,
    message_id BIGINT,
    voice_channel_id BIGINT,
    PRIMARY KEY (guild_id, message_id)
);

CREATE TABLE IF NOT EXISTS lobby_created_voice_channels_ids (
    guild_id BIGINT,
    channel_creator_category_id BIGINT,
    lobby_category_id BIGINT,
    PRIMARY KEY (guild_id, channel_creator_category_id)
);

-- endregion

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









CREATE TABLE IF NOT EXISTS bot_author (
    user_id BIGINT PRIMARY KEY
);
insert into bot_author (user_id) values (389787190986670082);

CREATE TABLE IF NOT EXISTS guild (
    id BIGINT PRIMARY KEY,
    owner_id BIGINT
);

CREATE TABLE IF NOT EXISTS guild_sync (
    guild_id BIGINT REFERENCES guild(id) PRIMARY KEY,
    member_name BOOLEAN DEFAULT FALSE,
    member_roles BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS guild_member (
    guild_id BIGINT REFERENCES guild(id),
    id BIGINT UNIQUE,
    nick TEXT,
    PRIMARY KEY (guild_id, id)
);

-- CREATE TABLE IF NOT EXISTS guild_restore_role (
-- --     guild_id BIGINT REFERENCES guild(id),
-- --     id BIGINT PRIMARY KEY,
-- --     name TEXT
-- -- );

-- CREATE TABLE IF NOT EXISTS member_role
-- (
--     guild_id  BIGINT REFERENCES guild (id),
--     member_id BIGINT REFERENCES guild_member (id),
--     role_id BIGINT REFERENCES guild_restore_role(id),
--     PRIMARY KEY (member_id, guild_id, role_id)
-- );

CREATE TABLE IF NOT EXISTS goodbye_channel (
    guild_id BIGINT REFERENCES guild(id),
    id BIGINT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS creativity_footer_text (
    text TEXT,
    guild_id BIGINT REFERENCES guild(id) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS art_channel (
    guild_id BIGINT REFERENCES guild(id),
    id BIGINT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS meme_channel (
    guild_id BIGINT REFERENCES guild(id),
    id BIGINT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS emoji_reaction (
    guild_id BIGINT REFERENCES guild(id) PRIMARY KEY,
    _like TEXT,
    dislike TEXT
);

CREATE TABLE IF NOT EXISTS tournament_blacklist (
    guild_id BIGINT REFERENCES guild(id),
    user_id BIGINT,
    reason TEXT,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS journal (
    guild_id BIGINT REFERENCES guild(id),
    user_id BIGINT,
    notes TEXT[],
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS journal_log_channel (
    guild_id BIGINT REFERENCES guild(id),
    id BIGINT PRIMARY KEY
);

-- CREATE TABLE IF NOT EXISTS error_logs_channel (
--     id BIGINT PRIMARY KEY,
--     guild_id BIGINT REFERENCES guild(id)
-- );


-- region Lobbies
CREATE TABLE IF NOT EXISTS lobby_voice_channel_creator_settings (
    guild_id BIGINT REFERENCES guild(id),
    id BIGINT PRIMARY KEY,
    category_id_for_new_channel BIGINT,
    user_limit INT,
    custom BOOLEAN DEFAULT FALSE,
    role_needed BOOLEAN DEFAULT FALSE,
    text_channel_id BIGINT,
    log_needed BOOLEAN DEFAULT FALSE,
    default_name TEXT,
    role_not_found_message TEXT,
    channel_with_role_prefix TEXT,
    channel_without_role_prefix TEXT
);

CREATE TABLE IF NOT EXISTS lobby_voice_channel_creator_role (
    guild_id BIGINT REFERENCES guild(id),
    voice_channel_id BIGINT REFERENCES lobby_voice_channel_creator_settings(id),
    role_id BIGINT,
    PRIMARY KEY (voice_channel_id, role_id)
);

CREATE TABLE IF NOT EXISTS lobby_voice_channel_settings (
    guild_id BIGINT REFERENCES guild(id),
    user_id BIGINT,
    channel_name TEXT,
    bitrate INT,
    user_limit INT,
    channel_overwrites JSON,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS lobby_created_voice_channel (
    id BIGINT PRIMARY KEY,
    voice_creator_id BIGINT REFERENCES lobby_voice_channel_creator_settings(id)
);

CREATE TABLE IF NOT EXISTS lobby_voice_channel_author (
    voice_channel_id BIGINT PRIMARY KEY REFERENCES lobby_created_voice_channel(id),
    user_id BIGINT
);


CREATE TABLE IF NOT EXISTS lobby_message (
    id BIGINT,
    voice_channel_id BIGINT REFERENCES lobby_voice_channel_author(voice_channel_id),
    PRIMARY KEY (id, voice_channel_id)
);

-- CREATE TABLE IF NOT EXISTS lobby_voice_creators (
--     guild_id BIGINT REFERENCES guild(id),
--     channel_creator_id BIGINT,
--     user_limit INT,
--     category_id BIGINT,
--     PRIMARY KEY (guild_id, channel_creator_id)
-- );

-- alter table lobby_category_rank_roles rename to lobby_category_roles;
-- alter table lobby_category_rank_roles add default_name TEXT DEFAULT NULL;
-- alter table lobby_category_rank_roles add role_not_found_message TEXT DEFAULT NULL;
-- CREATE TABLE IF NOT EXISTS lobby_category_rank_roles (
--     guild_id BIGINT REFERENCES guild(id),
--     category_id BIGINT,
--     role_id BIGINT,
--     role_name TEXT,
--     role_needed BOOL DEFAULT FALSE,
--     default_name TEXT,
--     role_not_found_message TEXT,
--     PRIMARY KEY (guild_id, category_id, role_id)
-- );
-- alter table lobby_category_rank_roles add role_needed BOOL DEFAULT FALSE;

-- CREATE TABLE IF NOT EXISTS lobby_text_channel_ids (
--     guild_id BIGINT REFERENCES guild(id),
--     lobby_category_id BIGINT,
--     text_channel_id BIGINT,
--     PRIMARY KEY (guild_id, lobby_category_id)
-- );



-- CREATE TABLE IF NOT EXISTS lobby_messages (
--     guild_id BIGINT REFERENCES guild(id),
--     message_id BIGINT,
--     voice_channel_id BIGINT,
--     PRIMARY KEY (guild_id, message_id)
-- );

-- CREATE TABLE IF NOT EXISTS lobby_created_voice_channels_ids (
--     guild_id BIGINT REFERENCES guild(id),
--     channel_creator_category_id BIGINT,
--     lobby_category_id BIGINT,
--     PRIMARY KEY (guild_id, channel_creator_category_id)
-- );

-- endregion

CREATE TABLE IF NOT EXISTS ticket (
    guild_id BIGINT REFERENCES guild(id) PRIMARY KEY,
    button_cooldown INT,
    category_id BIGINT,
    closed_ticket_category_id BIGINT,
    logs_channel_id BIGINT,
    number INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ticket_roles (
    guild_id BIGINT REFERENCES guild(id) PRIMARY KEY,
    question_roles_ids BIGINT[],
    report_roles_ids BIGINT[],
    offer_roles_ids BIGINT[]
);

CREATE TABLE IF NOT EXISTS ticket_user_button_cooldown (
    guild_id BIGINT REFERENCES guild(id),
    user_id BIGINT REFERENCES guild_member(id),
    end_time TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS ticket_button_emojis (
    guild_id BIGINT REFERENCES guild(id) PRIMARY KEY,
    question_button TEXT,
    report_button TEXT,
    offer_button TEXT,
    close_button TEXT,
    delete_button TEXT
);









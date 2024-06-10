async def register_member_in_guild(pool, member_id, guild_id):
    query = ("INSERT INTO guild_member (id, guild_id) "
             "VALUES ($1, $2) "
             "ON CONFLICT (id, guild_id) DO NOTHING")
    await pool.execute(query, member_id,
                       guild_id)

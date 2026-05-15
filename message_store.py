import discord

async def find_or_create(client, channel_id, embed, view=None):
    ch = client.get_channel(channel_id)
    if not ch: return None
    async for msg in ch.history(limit=20):
        if msg.author == client.user:
            try:
                if view:
                    await msg.edit(embed=embed, view=view)
                else:
                    await msg.edit(embed=embed)
                return msg.id
            except:
                pass
    msg = await ch.send(embed=embed, view=view) if view else await ch.send(embed=embed)
    return msg.id

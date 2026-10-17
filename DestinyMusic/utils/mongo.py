# -----------------------------------------------
# 🔸 DestinyMusic Project
# 🔹 Developed & Maintained by: Zefron (https://github.com/zefronxd)
# 📅 Copyright © 2025 – All Rights Reserved
#
# 📖 License:
# This source code is open for educational and non-commercial use ONLY.
# You are required to retain this credit in all copies or substantial portions of this file.
# Commercial use, redistribution, or removal of this notice is strictly prohibited
# without prior written permission from the author.
#
# ❤️ Made with dedication and love by Zefron
# -----------------------------------------------


from typing import Dict, Union

from motor.motor_asyncio import AsyncIOMotorClient as MongoCli

from config import MONGO_DB_NAME, MONGO_DB_URI

mongo = MongoCli(MONGO_DB_URI)
db = mongo[MONGO_DB_NAME]

coupledb = db.couple



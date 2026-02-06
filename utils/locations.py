# -*- coding: utf-8 -*-
"""
地名映射配置
用于从文章标题/URL中识别城市和国家
"""

# 地名 → (country, city) 映射
# 按地名长度降序匹配，更具体的地名优先（如 "nusa dua" 优先于 "bali"）
LOCATION_MAP = {
    # Indonesia - 主要城市
    "jakarta": ("Indonesia", "Jakarta"),
    "bandung": ("Indonesia", "Bandung"),
    "surabaya": ("Indonesia", "Surabaya"),
    "yogyakarta": ("Indonesia", "Yogyakarta"),
    "lombok": ("Indonesia", "Lombok"),
    # Indonesia - Bali 区域（city 统一为 Bali）
    "bali": ("Indonesia", "Bali"),
    "ubud": ("Indonesia", "Bali"),
    "seminyak": ("Indonesia", "Bali"),
    "canggu": ("Indonesia", "Bali"),
    "sanur": ("Indonesia", "Bali"),
    "uluwatu": ("Indonesia", "Bali"),
    "kuta": ("Indonesia", "Bali"),
    "nusa dua": ("Indonesia", "Bali"),
    "jimbaran": ("Indonesia", "Bali"),
    "legian": ("Indonesia", "Bali"),
    # Indonesia - Gili 群岛（属于 Lombok）
    "gili": ("Indonesia", "Lombok"),
    # Singapore
    "singapore": ("Singapore", "Singapore"),
    # Thailand
    "bangkok": ("Thailand", "Bangkok"),
    "phuket": ("Thailand", "Phuket"),
    "chiang mai": ("Thailand", "Chiang Mai"),
    "pattaya": ("Thailand", "Pattaya"),
    "krabi": ("Thailand", "Krabi"),
    "koh samui": ("Thailand", "Koh Samui"),
    # Malaysia
    "kuala lumpur": ("Malaysia", "Kuala Lumpur"),
    "penang": ("Malaysia", "Penang"),
    "langkawi": ("Malaysia", "Langkawi"),
    "malacca": ("Malaysia", "Malacca"),
    "kl": ("Malaysia", "Kuala Lumpur"),
    # Vietnam
    "hanoi": ("Vietnam", "Hanoi"),
    "ho chi minh": ("Vietnam", "Ho Chi Minh"),
    "saigon": ("Vietnam", "Ho Chi Minh"),
    "da nang": ("Vietnam", "Da Nang"),
    "hoi an": ("Vietnam", "Hoi An"),
    "nha trang": ("Vietnam", "Nha Trang"),
    # Philippines
    "manila": ("Philippines", "Manila"),
    "cebu": ("Philippines", "Cebu"),
    "boracay": ("Philippines", "Boracay"),
    "palawan": ("Philippines", "Palawan"),
    # Japan
    "tokyo": ("Japan", "Tokyo"),
    "osaka": ("Japan", "Osaka"),
    "kyoto": ("Japan", "Kyoto"),
    "fukuoka": ("Japan", "Fukuoka"),
    "okinawa": ("Japan", "Okinawa"),
    "hokkaido": ("Japan", "Hokkaido"),
    "nagoya": ("Japan", "Nagoya"),
    # Korea
    "seoul": ("Korea", "Seoul"),
    "busan": ("Korea", "Busan"),
    "jeju": ("Korea", "Jeju"),
    # China / HK / Macau
    "hong kong": ("China", "Hong Kong"),
    "macau": ("China", "Macau"),
    "shanghai": ("China", "Shanghai"),
    "beijing": ("China", "Beijing"),
    "shenzhen": ("China", "Shenzhen"),
    "guangzhou": ("China", "Guangzhou"),
    # Australia
    "sydney": ("Australia", "Sydney"),
    "melbourne": ("Australia", "Melbourne"),
    "brisbane": ("Australia", "Brisbane"),
    "perth": ("Australia", "Perth"),
    "gold coast": ("Australia", "Gold Coast"),
    # India
    "mumbai": ("India", "Mumbai"),
    "delhi": ("India", "Delhi"),
    "goa": ("India", "Goa"),
    "bangalore": ("India", "Bangalore"),
    # UAE
    "dubai": ("UAE", "Dubai"),
    "abu dhabi": ("UAE", "Abu Dhabi"),
    # Europe
    "london": ("UK", "London"),
    "paris": ("France", "Paris"),
    "barcelona": ("Spain", "Barcelona"),
    "rome": ("Italy", "Rome"),
    "amsterdam": ("Netherlands", "Amsterdam"),
    "berlin": ("Germany", "Berlin"),
    # USA
    "new york": ("USA", "New York"),
    "los angeles": ("USA", "Los Angeles"),
    "san francisco": ("USA", "San Francisco"),
    "miami": ("USA", "Miami"),
    "las vegas": ("USA", "Las Vegas"),
    "seattle": ("USA", "Seattle"),
}

# 国家名识别列表（小写）
COUNTRY_NAMES = {
    "indonesia", "singapore", "thailand", "malaysia", "vietnam", "philippines",
    "japan", "korea", "china", "australia", "india", "uae", "dubai",
    "uk", "france", "spain", "italy", "germany", "netherlands",
    "usa", "america", "maldives", "sri lanka", "cambodia", "myanmar", "laos",
}

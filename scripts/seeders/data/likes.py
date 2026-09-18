# Define strategic like patterns
hybrid_recommendation_likes = {
    'sanjay_yadav11': [
        'priya_gurung2',  # Doctor - High compatibility
        'sita_rai4',  # Teacher - Medium compatibility
        'sunita_newar8',  # Accountant - Medium compatibility
        'anjali_chaudhary16',  # Lawyer - High compatibility
        'sabina_gharti18',  # Nurse - Medium compatibility
        'prabina_khadka20',  # Psychology Student - Medium compatibility
        'bina_chaudhary32',  # Corporate Lawyer - High compatibility
        'anita_shrestha38'  # Hotel Manager - Medium compatibility
    ],

    'rina_sherpa12': [
        'anil_magar5',  # Civil Engineer - Medium compatibility
        'mina_tamang6',  # Nurse - High compatibility
        'bikash_tharu9',  # Agriculture Specialist - Medium compatibility
        'karuna_gurung24',  # Social Worker - High compatibility
        'maya_tamang28',  # Community Health Worker - High compatibility
        'laxmi_limbu30',  # Primary Teacher - Medium compatibility
        'gita_gharti34',  # Nurse - High compatibility
        'sabina_khadka54'  # Psychology Student - Medium compatibility
    ],

    'amit_koiri13': [
        'bikash_tharu9',  # Agriculture Specialist - High compatibility
        'dilip_tharu27',  # Agriculture Officer - High compatibility
        'hari_yadav29',  # Dairy Farmer - Medium compatibility
        'krishna_koiri39',  # Agriculture Specialist - High compatibility
        'gita_tharu45',  # Agriculture Officer - High compatibility
        'hari_koiri57',  # Agriculture Specialist - High compatibility
        'rekha_yadav47'  # Bank Officer - Medium compatibility
    ],

    'saraswati_dahal14': [
        'rohan_thapa3',  # Business Owner - High compatibility
        'rajesh_karki7',  # Government Officer - High compatibility
        'sanjay_yadav11',  # Marketing Manager - Medium compatibility
        'niraj_basnet15',  # Architect - Medium compatibility
        'anjali_chaudhary16',  # Lawyer - High compatibility
        'sarita_dahal40',  # Journalist - High compatibility
        'bimala_sharma41',  # Software Developer - Medium compatibility
        'rajiv_mishra42'  # Business Consultant - High compatibility
    ],

    'niraj_basnet15': [
        'sita_rai4',  # Teacher - Medium compatibility
        'sunita_newar8',  # Accountant - Medium compatibility
        'shristi_shakya26',  # Graphic Designer - High compatibility
        'prabina_khadka20',  # Psychology Student - Medium compatibility
        'anita_shrestha38',  # Hotel Manager - Medium compatibility
        'sanjana_rai43',  # Environmental Scientist - Medium compatibility
        'pramila_gurung49',  # Nurse - Medium compatibility
        'anju_shrestha56'  # Hotel Manager - High compatibility
    ],

    'anjali_chaudhary16': [
        'aarav_sharma1',  # Software Engineer - High compatibility
        'rohan_thapa3',  # Business Owner - High compatibility
        'rajesh_karki7',  # Government Officer - High compatibility
        'saraswati_dahal14',  # Journalist - High compatibility
        'bina_chaudhary32',  # Corporate Lawyer - High compatibility
        'arjun_chaudhary50',  # Corporate Lawyer - High compatibility
        'bimala_sharma41',  # Software Developer - Medium compatibility
        'rajiv_mishra42'  # Business Consultant - High compatibility
    ],

    'ramesh_poudel17': [
        'priya_gurung2',  # Doctor - High compatibility
        'sunita_newar8',  # Accountant - High compatibility
        'sabina_gharti18',  # Nurse - Medium compatibility
        'prabina_khadka20',  # Psychology Student - Medium compatibility
        'nabin_poudel33',  # Bank Manager - High compatibility
        'rekha_yadav47',  # Bank Officer - High compatibility
        'sunil_poudel51',  # Bank Manager - High compatibility
        'bimala_sharma41'  # Software Developer - Medium compatibility
    ],

    'sabina_gharti18': [
        'mina_tamang6',  # Nurse - High compatibility
        'sita_rai4',  # Teacher - Medium compatibility
        'karuna_gurung24',  # Social Worker - High compatibility
        'maya_tamang28',  # Community Health Worker - High compatibility
        'gita_gharti34',  # Nurse - High compatibility
        'laxmi_limbu30',  # Primary Teacher - Medium compatibility
        'laxmi_gharti52',  # Community Health Worker - High compatibility
        'pramila_gurung49'  # Nurse - High compatibility
    ],

    'kiran_bhandari19': [
        'aarav_sharma1',  # Software Engineer - High compatibility
        'rohan_thapa3',  # Business Owner - Medium compatibility
        'niraj_basnet15',  # Architect - Medium compatibility
        'deepak_rana21',  # Electrical Engineer - Medium compatibility
        'prakash_bhandari35',  # IT Consultant - High compatibility
        'rohit_bhandari53',  # IT Consultant - High compatibility
        'rajiv_mishra42',  # Business Consultant - Medium compatibility
        'manoj_khatri46'  # Mechanical Engineer - Medium compatibility
    ],

    'prabina_khadka20': [
        'sita_rai4',  # Teacher - Medium compatibility
        'saraswati_dahal14',  # Journalist - Medium compatibility
        'anjali_chaudhary16',  # Lawyer - Medium compatibility
        'sangita_khadka36',  # Psychology Student - High compatibility
        'sabina_khadka54',  # Psychology Student - High compatibility
        'sanjana_rai43',  # Environmental Scientist - Medium compatibility
        'pramila_gurung49',  # Nurse - Medium compatibility
        'sita_dahal58'  # Journalist - Medium compatibility
    ],

    'deepak_rana21': [
        'anil_magar5',  # Civil Engineer - Medium compatibility
        'bikash_tharu9',  # Agriculture Specialist - Medium compatibility
        'dilip_tharu27',  # Agriculture Officer - Medium compatibility
        'rabin_rana37',  # Electrical Engineer - High compatibility
        'kumar_rana55',  # Electrical Engineer - High compatibility
        'manoj_khatri46',  # Mechanical Engineer - Medium compatibility
        'sandeep_limbu48',  # Social Worker - Medium compatibility
        'hari_koiri57'  # Agriculture Specialist - Medium compatibility
    ],

    'suman_shrestha22': [
        'priya_gurung2',  # Doctor - Medium compatibility
        'sunita_newar8',  # Accountant - Medium compatibility
        'sabina_gharti18',  # Nurse - Medium compatibility
        'anita_shrestha38',  # Hotel Manager - High compatibility
        'anju_shrestha56',  # Hotel Manager - High compatibility
        'pramila_gurung49',  # Nurse - Medium compatibility
        'bimala_sharma41',  # Software Developer - Medium compatibility
        'rekha_yadav47'  # Bank Officer - Medium compatibility
    ]
}

mutual_like_pairs = [
    # User 32 (Bina Chaudhary - Corporate Lawyer) mutual pairs - Will create matches
    ('bina_chaudhary32', 'arjun_chaudhary50'),  # Both lawyers - High compatibility
    ('bina_chaudhary32', 'rohan_thapa3'),  # Business owner - Medium compatibility
    ('bina_chaudhary32', 'rajesh_karki7'),  # Government officer - Medium compatibility
    ('bina_chaudhary32', 'saraswati_dahal14'),  # Journalist - Medium compatibility

    # User 33 (Nabin Poudel - Bank Manager) mutual pairs - Will create matches
    ('nabin_poudel33', 'ramesh_poudel17'),  # Both bank managers - High compatibility
    ('nabin_poudel33', 'rekha_yadav47'),  # Bank officer - High compatibility
    ('nabin_poudel33', 'sunita_newar8'),  # Accountant - High compatibility
    ('nabin_poudel33', 'sunil_poudel51'),  # Bank manager - High compatibility

    # User 34 (Gita Gharti - Nurse) mutual pairs - Will create matches
    ('gita_gharti34', 'mina_tamang6'),  # Both nurses - High compatibility
    ('gita_gharti34', 'karuna_gurung24'),  # Social worker - Medium compatibility
    ('gita_gharti34', 'maya_tamang28'),  # Health worker - High compatibility
    ('gita_gharti34', 'sabina_gharti18'),  # Nurse - High compatibility

    # User 35 (Prakash Bhandari - IT Consultant) mutual pairs - Will create matches
    ('prakash_bhandari35', 'kiran_bhandari19'),  # Both IT consultants - High compatibility
    ('prakash_bhandari35', 'aarav_sharma1'),  # Software engineer - High compatibility
    ('prakash_bhandari35', 'bimala_sharma41'),  # Software developer - High compatibility
    ('prakash_bhandari35', 'rohit_bhandari53'),  # IT consultant - High compatibility

    # User 36 (Sangita Khadka - Psychology Student) mutual pairs - Will create matches
    ('sangita_khadka36', 'sita_rai4'),  # Teacher - Medium compatibility
    ('sangita_khadka36', 'laxmi_limbu30'),  # Primary teacher - Medium compatibility
    ('sangita_khadka36', 'sandeep_limbu48'),  # Social worker - High compatibility
    ('sangita_khadka36', 'prabina_khadka20'),  # Psychology student - High compatibility

    # User 37 (Rabin Rana - Electrical Engineer) mutual pairs - Will create matches
    ('rabin_rana37', 'anil_magar5'),  # Civil engineer - Medium compatibility
    ('rabin_rana37', 'deepak_rana21'),  # Electrical engineer - High compatibility
    ('rabin_rana37', 'kumar_rana55'),  # Electrical engineer - High compatibility
    ('rabin_rana37', 'dilip_tharu27'),  # Agriculture officer - Medium compatibility

    # User 38 (Anita Shrestha - Hotel Manager) mutual pairs - Will create matches
    ('anita_shrestha38', 'suman_shrestha22'),  # Both hotel managers - High compatibility
    ('anita_shrestha38', 'sanjay_yadav11'),  # Marketing manager - Medium compatibility
    ('anita_shrestha38', 'anju_shrestha56'),  # Hotel manager - High compatibility
    ('anita_shrestha38', 'priya_gurung2'),  # Doctor - Medium compatibility

    # User 39 (Krishna Koiri - Agriculture Specialist) mutual pairs - Will create matches
    ('krishna_koiri39', 'bikash_tharu9'),  # Agriculture specialist - High compatibility
    ('krishna_koiri39', 'amit_koiri13'),  # Agriculture specialist - High compatibility
    ('krishna_koiri39', 'hari_koiri57'),  # Agriculture specialist - High compatibility
    ('krishna_koiri39', 'gita_tharu45'),  # Agriculture officer - High compatibility

    # User 40 (Sarita Dahal - Journalist) mutual pairs - Will create matches
    ('sarita_dahal40', 'saraswati_dahal14'),  # Both journalists - High compatibility
    ('sarita_dahal40', 'anjali_chaudhary16'),  # Lawyer - Medium compatibility
    ('sarita_dahal40', 'sita_dahal58'),  # Journalist - High compatibility
    ('sarita_dahal40', 'rajesh_karki7')  # Government officer - Medium compatibility
]

{
"name": "GESTION DES ADHERENT",
"version": "0.1",
"summary": """Gestion des adhérents""",
"category":"rh",
"installable" : True,
'author': 'Sekkak oussama',
'depends':['base','report','hr'],
"auto_install": False,
"application" : True,
"description" : """
            ce module a pour objectif de gerer les adhérents d'une salle de sport""",
"data": [
        'data/data.xml',
        'views/golden_gym_view.xml',
        'views/action_automatique.xml',
        'views/ir_sequence.xml',
        'views/example_webpage.xml',
        'report/paper_format.xml',
        'report/report.xml',
        'report/facturation.xml',
        'wizard/calcule_paiement_abonnement.xml',
        'security/gestion_adherent_security.xml',
        'security/ir.model.access.csv',
        'wizard/recette_view.xml',
        'report/fiche_medicale.xml'
    ] ,
    


    }

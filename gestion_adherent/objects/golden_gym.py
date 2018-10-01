# -*- encoding: utf-8 -*-

from openerp.osv import  osv, orm
import time
from datetime import date
from datetime import datetime, timedelta
import base64
import xmlrpclib
from openerp import pooler, sql_db , models, api ,fields
from openerp.api import Environment
from openerp.tools.translate import _



class gym_adherent(models.Model):
	 

	_name = "gym.adherent"


	_order='abonnement_id desc'

	_FIDELITE = [
	('0', ''),
	('1', 'Débutant'),
	('2', 'En progrés'),
	('3', 'Compétant'),
	('4', 'Profésionnel')
	]
	_sexe = [
	('masc', 'Garçon'),
	('fem', 'Fille')
	]

	_GS = [
	('0', ''),
	('1', 'A'),
	('2', 'B'),
	('3', 'AB'),
	('4', 'O')
	]


	_GS2 = [
	('pos', 'Positif'),
	('neg', 'Négatif')
	]


	def name_get(self, cr, user, ids, context=None):
	    if context is None:
	        context = {}
	    if isinstance(ids, (int, long)):
	        ids = [ids]
	    if not len(ids):
	        return []
	    def _name_get(d):
	        name = d.get('name','')
	        prenom = d.get('prenom',False)
	        # Vivek
	        #End
	        if prenom:
	            name = '%s %s' % (name,prenom)
	        return (d['id'], name)


	    result = []
	    for adherent in self.browse(cr, user, ids, context=context):
	        # Vivek
	        prd_temp = self.pool.get('gym.adherent').browse(cr, user, adherent.id, context=context)
	        # End
	        mydict = {
	                      'id': adherent.id,
	                      'name': prd_temp.name,
	                      #vivek
	                      'prenom': prd_temp.prenom,
	                      }
	        result.append(_name_get(mydict))
	    return result

	#añadir tratamientos cuando creamos un miembro
	def create(self,cr, uid, vals, context=None):
		valores = {}
		rec = super(gym_adherent, self).create(cr, uid, vals, context=context)	
		#preparar los campos del miembro y su suscipcion para añadirlos en el historial de pagos despues su creacion
		ab = vals.get('abonnement_id')
		tarif_tree = vals.get('tarif_tree')
		paiement_ab = self.pool.get('paiement.abonnement')
		abonnement = self.pool.get('gym.abonnement').browse(cr, uid,ab,context=context)
		search_ids = self.pool.get('gym.adherent').search(cr, uid,[],context=context)
		#last_id = self.env['gym.adherent'].search([])[-1] ce n'est pas utile car les id ne sont pas (sorted)

		#buscar el ultimo record creado en la tabla gym_adherent(miembros)
		cr.execute('select "id" from "gym_adherent" order by "id" desc limit 1')
		id_returned = cr.fetchone()
		last_id = self.pool.get('gym.adherent').browse(cr, uid,id_returned[0],context=context)
		#añadir el nombre del miembro a su suscripcion despues guardarla
		name= abonnement.name
		name = name.replace("AB", last_id.name)
		last_id.write({'date':abonnement.jusqua})
		# con la creacion de una nueva suscripcion eso significa que hay un pago, por eso vamos a recuperar los campos 
		#como el modo de pago y fecha de debute y fin de supscripcion y el suma...., para crear un pago.
		abonnement.write({'name':name})
		"""
		valores['mode_p']=abonnement.mode_p
		valores['debut']=abonnement.debut
		valores['fin']=abonnement.jusqua
		valores['abonnement_id']=ab
		valores['adherent']= last_id.id
		if abonnement.mode_p == 'mois':
			valores['tarif_a_payer']= (((abonnement.type_abonn.tarif + abonnement.tarif_garderier) * abonnement.get_total_mois(abonnement.debut,abonnement.jusqua)) - abonnement.taux_remise ) + abonnement.tarif_scholar
		if abonnement.mode_p == 'jours':
			valores['tarif_a_payer']= (( ( abonnement.type_abonn.tarif + abonnement.tarif_garderier) * abonnement.get_total_mois(abonnement.debut,abonnement.jusqua) ) - abonnement.taux_remise ) + abonnement.tarif_scholar
		paire_returned = paiement_ab.create(cr, uid,valores,context=context)
		p = paiement_ab.browse(cr, uid,paire_returned,context=context)
		p.write({'tarif_a_payer':( ( (abonnement.type_abonn.tarif + abonnement.tarif_garderier) * abonnement.get_total_mois(abonnement.debut,abonnement.jusqua) ) - abonnement.taux_remise ) + abonnement.tarif_scholar})
		"""
		return rec

	@api.multi
	def write(self,vals):
		for record in self:
			#caso donde no hay modificacion de este campo 'solde', hay que añadirlo al diccionario vals con su valor , para evitar el bug key error.
			if not vals.get('solde'):
				vals.update({'solde':None})
				vals['solde']= record.solde
			if not vals.get('cmpt'):
				vals.update({'cmpt':None})
				vals['cmpt']= record.cmpt

			date_time = date.today()
			d_today = datetime.strptime(str(date_time), "%Y-%m-%d")
			# despues 6 dias cambiamos el grupo del miembro al grupo 'Absents = Ausencias'
			if not vals.get('date'):
						vals.update({'date':None})
						vals['date']= record.date
			d1 = datetime.strptime(str(vals['date']), "%Y-%m-%d")
			EndDate = d1 + timedelta(days=6)
			old_group = record.env[('gym.group')].search([('name','=','Absents')]).id
			if old_group:
				if EndDate < d_today:
					if not vals.get('group_id'):
						vals.update({'group_id':None})
					vals['group_id']= old_group
			#en caso no existe el grupo Absents , hay que crearlo
			else :
					raise osv.except_osv(
								_('Attention!'),
								_('Veillez vérifier l\'existance du groupe "Absents" svp!\n'+
								'-Ajoutez le groupe en cas n\'existe pas \n'+
								'-Ecrivez le nom du groupe Correctement ( Absents )'))
		rec = super(gym_adherent, self).write(vals)
		return rec


	def _set_image(self, cr, uid, id, name, value, args, context=None):
		return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

	def _get_image(self, cr, uid, ids, name, args, context=None):
		result = dict.fromkeys(ids, False)
		for obj in self.browse(cr, uid, ids, context=context):
			result[obj.id] = tools.image_get_resized_images(obj.image)
		return result
	"""
	# recuperar los dias restantes de la suscripcion de un miembro desde su suscripcion
	@api.one
	@api.depends('abonnement_id.solde')
	def _paiement_auj_solde(self):
				res = self.abonnement_id.solde
				valor = self.update({'solde':res})
				return valor
	"""
	@api.one
	@api.depends('abonnement_id.solde')
	def _paiement_auj_solde(self):
				res = self.abonnement_id._compute_solde()
				self.solde = res
				return res
	# recuperar las ausencias de un miembro desde su suscription
	@api.one
	@api.depends('abonnement_id.cmpt')
	def _verifier_retard(self):
				res = self.abonnement_id.cmpt
				valor = self.update({'cmpt':res})
				return valor
	#verificar si el miembro ha pagado la suscripcion
	@api.one
	@api.depends('solde')
	def _paiement_auj(self):
				if self.solde <= 0:
					valor = self.update({'mois_payee':False})
					return valor
				else:
					valor = self.update({'mois_payee':True})
					return valor

	#elegir un color para cada grupo
	@api.one
	@api.depends('group_id','solde')
	def change_color_expire_ab(self):
		if self.group_id.name == 'Absents':
			self.color = 3
		else: 
			if self.solde == 0:
				self.color = 2
			elif self.solde < 60 and self.solde >= 10:
				self.color = 4
			elif self.solde < 10:
				self.color = 3
			else:
				self.color = 5
		return self.color

	"""Aqui hay los campos del clase"""
	name = fields.Char('Nom Enfant', required=True)
	date_debut = fields.Date('Date debut',default=fields.Datetime.now)
	prenom = fields.Char('Prénom Enfant')
	cn_id = fields.Char('Adresse')
	date_nais =  fields.Date('Date de naissance')
	lieu_nais =  fields.Char('Lieu de naissance')
	fidelite =fields.Selection(_FIDELITE,'Catégorie')
	mois_payee = fields.Boolean(compute='_paiement_auj')
	abonnement_id = fields.Many2one('gym.abonnement','Abonnement' , required=True)
	solde = fields.Integer(string='solde',compute='_paiement_auj_solde')
	tarif_tree = fields.Float(string='Montant a payer',related="abonnement_id.type_abonn.tarif" ,store=True,readonly=False)
	image_medium =fields.Binary(compute='_get_image', fnct_inv=_set_image,
			string="Medium-sized photo", multi="_get_image",
			store = True,
			help="Medium-sized photo of the employee. It is automatically "\
				 "resized as a 128x128px image, with aspect ratio preserved. "\
				 "Use this field in form views or some kanban views.")
	image =fields.Binary(string="Photo")

	cmpt = fields.Integer('Retardement',compute='_verifier_retard')
	sexe =fields.Selection(_sexe,'Sexe')
	group_id= fields.Many2one('gym.group',string='Groupe',required=True)
	date = fields.Date('Date de prochaine paiement')
	color = fields.Integer('Color index', default=0,compute='change_color_expire_ab',readonly=False)
	parents = fields.One2many('parent.child','child','Tuteurs')
	poids = fields.Float('Poids')
	taille= fields.Float('Taille')
	groupe_sanguin = fields.Selection(_GS,'Groupe Sanguin')
	rhesus = fields.Selection(_GS2,'Rhesus')
	maladie_grave = fields.Boolean("Maladie ou Interventions antèrieures graves ( lesquelles et quand )?")
	maladie_grave_texte = fields.Text('')
	allergique = fields.Boolean("L'enfant est-il alergique ou sensible à certains médicaments ?")
	allergique_texte = fields.Text('')
	regime = fields.Boolean("L'enfant suit-il un régime particulier ?")
	regime_texte = fields.Text('')
	medicament = fields.Boolean("L'enfant doit-il prendre des médicaments durant la journée de classe ?")
	medicament_texte = fields.Text('')
	diabete = fields.Boolean(" Diabète")
	asthme = fields.Boolean("Asthme")
	affection_ca = fields.Boolean("Affection Cardiaque")
	epilepsie = fields.Boolean("Epilepsie")
	affection_cu = fields.Boolean("Affection cutanée")
	pere = fields.Char('Père')
	mere = fields.Char('Mère')
	partner_mobile = fields.Char('Mobile')

	"""Fin declaracion de los campos"""


	#abrir la pantalla de la venta
	@api.multi
	def open_wizard(self):
		
		return {
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'paiement.abonnement',
			'target': 'new',
			'type': 'ir.actions.act_window',
			'context': {'current_id': self.id}
		} 



#class de suscripciones
class gym_abonnement(models.Model):
	_name = "gym.abonnement"


	_order='jusqua desc'

	_mode_paiement = [
	('jours','Par Jour'),
	('mois', 'Par Mois')
	]

	#calcular los dias de ausencias
	@api.multi
	@api.depends('jusqua')
	def _compute_cpmt(self):
		dt = str(date.today())
		for record in self:
			if record.debut and record.jusqua and dt:
				if dt > record.jusqua:
					d1 = datetime.strptime(dt, "%Y-%m-%d")
					d2 = datetime.strptime(record.jusqua, "%Y-%m-%d")
					record.cmpt = (d2 - d1).days
	#calcular el precio de la suscripcion segun los dias pagados
	@api.model
	def get_total_mois(self,debut,fin):
		nb_mois= 0
		d1 = datetime.strptime(fin, "%Y-%m-%d")
		d2 = datetime.strptime(debut, "%Y-%m-%d")
		delta = 0
		if self.mode_p == 'jours':
			#delta = float(((d1 - d2).days+1)/30.0)
			"""
			#if int(d1.month) == 01 or int(d1.month) == 03 or int(d1.month) == 05 or int(d1.month) == 07 or int(d1.month) == 08 or int(d1.month) == 10 or int(d1.month) == 12:
			if  abs((d1-d2).days) == 30:
				delta = float(((d1 - d2).days)/30.0)
			#exceotion pour mois février
			if int(d1.month) == 02 and int(d2.month) == 02 and abs((d1-d2).days) == 28:
				delta = float(((d1 - d2).days+2)/30.0)
			if int(d1.month) == 02 and int(d2.month) == 02 and abs((d1-d2).days) == 27:
				delta = float(((d1 - d2).days+3)/30.0)
			"""
			#self.solde = self.solde_jour
			delta = self.solde_jour/30.0

			#if (int(d1.month) - int(d2.month)) == 3 and abs((d1-d2).days) == 91 or abs((d1-d2).days) == 92:
				#delta = 90/30.0
		if self.mode_p == 'mois':
			delta = d1.month - d2.month
		if d1 > d2 :
			nb_mois = float((d1.year - d2.year)*12) + delta
		self.nb_mois = nb_mois
		return nb_mois

	@api.multi
	@api.depends('jusqua')
	def _compute_solde(self):
		for record in self:
			dt = str(date.today())
			"""
			if record.solde_jour and record.mode_p == 'jours':
				record.solde = record.solde_jour
			else:
			"""
			result = 0
			if record.jusqua and dt:
					if dt < record.jusqua:
						d1 = datetime.strptime(dt, "%Y-%m-%d")
						d2 = datetime.strptime(record.jusqua, "%Y-%m-%d")
						delta = abs((d2 - d1).days)
						result = delta
						if record.solde_jour and record.mode_p == 'jours' and delta >= record.solde_jour:
							res = (delta - record.solde_jour)
							result = delta - res					
					else:
						result = 0
			record.solde = result
			return result

	"""Aqui hay los campos del clase"""
	nb_mois = fields.Float(compute='get_total_mois')
	name = fields.Char('Ref', readonly=True)
	debut = fields.Date('Depuis',default=fields.Datetime.now)
	jusqua = fields.Date('jusqu\' à',default=fields.Datetime.now)
	type_abonn =  fields.Many2one('type.abonnement','Type Abonnement')
	solde = fields.Integer(compute='_compute_solde')
	cmpt = fields.Integer('Retardement',compute='_compute_cpmt')
	garderier = fields.Boolean('Ajouter Garderie ?')
	tarif_garderier = fields.Float('Tarif garderie')
	mode_p =fields.Selection(_mode_paiement,'Mode paiement',default='mois')
	solde_jour = fields.Integer('Nombre jours')
	remise = fields.Boolean('Ajouter une remise mensuelle ?')
	taux_remise = fields.Float('Remise')
	"""Fin declaracion de los campos"""

	#crear un sequencia con abreviación de meses para los pagos
	@api.model
	def create(self,vals):
		month = (date.today()).month
		mois_en_lettre = ''
		if month == 1: 
			mois_en_lettre = 'Jan'
		if month == 2:
			mois_en_lettre = 'Fév'
		if month == 3:
			mois_en_lettre = 'Mars'
		if month == 4:
			mois_en_lettre = 'Avl'
		if month == 5:
			mois_en_lettre = 'Mai'
		if month == 6:
			mois_en_lettre = 'Jui'
		if month == 7:
			mois_en_lettre = 'juil'
		if month == 8:
			mois_en_lettre = 'Aout'
		if month == 9:
			mois_en_lettre = 'Sept'
		if month == 10:
			mois_en_lettre = 'Oct'
		if month == 11:
			mois_en_lettre = 'Nov'
		if month == 12:
			mois_en_lettre = 'Déc'

		#recuperar el ID currente del objeto miembro
		gym_ids = self._context.get('active_ids', [])
		gym_adh = self.env[('gym.adherent')].browse(gym_ids)
		sequence=self.env[('ir.sequence')].get('reg_code_abonn')
		ref = 'AB'
		ref = sequence+'/'+ref+'/'+mois_en_lettre+''+str((date.today()).year)
		vals['name']=ref

		return super(gym_abonnement, self).create(vals)



	#pour décrementer le solde par rapport au jours 
	#para decrementar el nombre de los dias (su llamada esta en planificar accion)
	"""
	def process_dias_restantes(self, cr, uid, context=None):
		scheduler_line_obj = self.pool.get('gym.abonnement')
		#Contains all ids for the model scheduler.demo
		scheduler_line_ids = self.pool.get('gym.abonnement').search(cr, uid, [])   
		#Loops over every record in the model scheduler.demo
		for scheduler_line_id in scheduler_line_ids :
			#Contains all details from the record in the variable scheduler_line
			scheduler_line =scheduler_line_obj.browse(cr, uid,scheduler_line_id ,context=context)
			numberOfUpdates = scheduler_line.solde_jour
			numberOfUpdates_cmpt = scheduler_line.cmpt
			#Prints out the name of every record.
			_logger.info('line: ' + scheduler_line.name)
			#Update the record
			if numberOfUpdates > 0 :
				scheduler_line_obj.update(cr, uid, scheduler_line_id, {'solde': int(numberOfUpdates -1)}, context=context)
			else: 
				scheduler_line_obj.update(cr, uid, scheduler_line_id, {'cmpt': int(numberOfUpdates_cmpt-1)}, context=context)
	"""

	#pour décrementer le solde par rapport au jours 
	#para decrementar el nombre de los dias (su llamada esta en planificar accion)

	#onchange para verificar si el dia del debute < dia de fin de suscrip
	@api.onchange('jusqua','debut')
	def verifier_date(self):

		for record in self:
			record.nb_mois = self.get_total_mois(record.debut,record.jusqua)
			dt = str(date.today())
			if record.debut > record.jusqua:
				raise osv.except_osv(
					_('Attention!'),
					_('Date debut est supperieur au date Fin !.'))
			if 	record.jusqua < dt:
				record.solde = 0
				raise osv.except_osv(
					_('Attention!'),
					_('Date Fin est Inferieure a la date d\'aujourd\'hui !.'))
	
				

#tipo de suscripciones
class type_abonnement(models.Model):   
	_name='type.abonnement'


	name = fields.Char('Type abonnement')
	type_id = fields.Integer()
	tarif = fields.Float('Tarif')
	options = fields.Text('Options')


_JOURS = [
	('0', 'Samedi'),
	('1', 'Dimanche'),
	('2', 'Lundi'),
	('3', 'Mardi'),
	('4', 'Mercredi'),
	('5', 'Jeudi'),
	('6', 'Vendredi'),
	] 


class jour_heure(models.Model):

	_name = 'jour.heure'


	day =fields.Selection(_JOURS,'les jours ')
	heure_debut = fields.Float('Heure Debut')
	heure_fin =fields.Float('Heure fin')
	jour_id = fields.Many2one('emplois.du.temps', 'jour heure', invisible=True)
	program_id = fields.Many2one('gym.programme','Programme')



#planning
class emplois_du_temps(models.Model):
	_name = 'emplois.du.temps'


	name=fields.Char('Planning')
	jour_heure = fields.One2many('jour.heure', 'jour_id', 'Journée')

#programas de gimnasio
class gym_programme(models.Model):
	_name = 'gym.programme'

	name = fields.Char('Programme')
	date_to = fields.Datetime('Date debut')
	date_from = fields.Datetime('Date fin')
	tache_ids = fields.One2many('gym.tache','program_id','Activité')
	moniteurs = fields.One2many('hr.employee','program_id','Moniteurs')


class hr_employee(models.Model):
	_inherit = 'hr.employee'
	program_id = fields.Many2one('gym.programme','Programme')



class gym_tache(models.Model):
	_name = 'gym.tache'

	activity = fields.Char('Activité')
	duree = fields.Float('Durée')
	group_id= fields.Many2one('gym.group','Groupe')
	program_id = fields.Many2one('gym.programme','Programme')

#clase de grupos
class gym_group(models.Model):
	_name = 'gym.group'
	_order = 'sequence desc'
	name = fields.Char('Groupe')
	sequence = fields.Integer('Séquence')
	membres = fields.One2many('gym.adherent','group_id','Membres')
	moniteur = fields.Many2one('hr.employee','Moniteur')
	emploisT = fields.Many2one('emplois.du.temps','Emplois du Temps')


class parent_child(models.Model):
	_name = 'parent.child'
	_order = 'name desc'

	name = fields.Char('Nom Tuteur')
	prenom = fields.Char('Prénom Tuteur')
	cn_id = fields.Char('Num CIN')
	mobile = fields.Char('Mobile')
	adress = fields.Char('Adresse Domicile')
	photo = fields.Binary('Photo')
	child = fields.Many2one('gym.adherent','Enfant')
	color = fields.Integer('Color index', default=0,readonly=False)




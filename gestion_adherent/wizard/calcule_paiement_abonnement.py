# -*- encoding: utf-8 -*-

from openerp.osv import  osv, orm
import time
from datetime import date
from datetime import datetime
import base64
import xmlrpclib
from openerp import pooler, sql_db , models, api ,fields
from openerp.api import Environment
from openerp.tools.translate import _
import convertion


class paiement_abonnement(osv.Model):
	_name = "paiement.abonnement"

	_order='create_date desc'

	_inherit = [
		'mail.thread'
	]

	_mode_paiement = [
	('jours','Par Jour'),
	('mois', 'Par Mois'),
	('seance', 'Par séance')
	]

	_STATE = [
	('total','Totalement payée'),
	('partiel', 'Partièlement payée'),
	]

	_MODALITE = [
	('espece','Par Espèce'),
	('cheque', 'Par Cheque'),
	]


	def name_get(self, cr, uid, ids, context=None):
		if not len(ids):
			   return []
		res=[]
		for abonnement in self.browse(cr, uid, ids,context=context):
			res.append((abonnement.id,  str(abonnement.adherent.name)+" "+str(abonnement.adherent.prenom)))            
		return res




	@api.model
	def get_default_date_debut(self):
		gym_ids = self._context.get('active_ids', [])
		gym_adh = self.env[('gym.adherent')].browse(gym_ids)
		return gym_adh.date

	@api.one
	@api.onchange('net_payee','tarif_a_payer')
	def get_reste_a_payer(self):
		self.reste_a_payer = 0.0
		if self.net_payee and self.tarif_a_payer:
			self.reste_a_payer =  self.tarif_a_payer - self.net_payee
			if self.reste_a_payer == 0.0:
				self.state = 'total'
			else:
				self.state ='partiel'
	
	"""Aqui hay los campos del clase primera lista"""
	name=fields.Char('Référence')
	debut = fields.Date('Date debut',default=get_default_date_debut)
	fin = fields.Date('Date fin',default=fields.Datetime.now)
	#ajouter le 12/09/2018
	solde_jour = fields.Integer('Nombre jours')
	####
	unit = fields.Float('Tarif Séance')
	nb_seance = fields.Integer('Nombre Séance',default=1)
	options= fields.One2many('gym.acheter.option','paiement_id','Options')
	services = fields.One2many('gym.acheter.service','paiement_id','Services')
	mode_p =fields.Selection(_mode_paiement,'Mode paiement')
	is_options = fields.Boolean('Acheter Produit/Service ?')
	garderier = fields.Boolean('Cochez Garderie')
	tarif_garderier = fields.Float('Tarif Garderie',default=300.0)
	nb_jour_garderier = fields.Integer('Nombre Jours de garderie')
	state = fields.Selection(_STATE,'Etat facture')
	modalite = fields.Selection(_MODALITE,'Modalité de paiement')
	add_remise = fields.Boolean('Ajouter remise')
	remise = fields.Float('Remise')
	scholar = fields.Boolean('Ajouter Frais scolaire ?')
	tarif_scholar = fields.Float('Frais Scolaire',default=0.0)
	#recuperar toda la suma de los productos vendidos o los servicios a pagar



	@api.multi
	@api.depends('options','services')
	def _get_total_options(self):
		total = 0.0
		for option in self:
			option.somme_options = sum(op.somme for op in option.options) + sum(op.somme_service for op in option.services)
			total = option.somme_options
		return total

	somme_options = fields.Float(compute='_get_total_options')



	@api.multi
	def get_default_abonnement_id(self):
		gym_ids = self._context.get('active_ids', [])
		gym_adh = self.env[('gym.adherent')].browse(gym_ids)
		return gym_adh.abonnement_id.id


	@api.depends('adherent')
	def get_default_tarif(self):
		tarif= self.adherent.tarif_tree
		if tarif:
				self.tarif_abonnement = tarif
		return tarif
	tarif_abonnement = fields.Float(compute='get_default_tarif')


	@api.model
	def get_total_mois(self,debut,fin):
		nb_mois= 0
		d1 = datetime.strptime(fin, "%Y-%m-%d")
		d2 = datetime.strptime(debut, "%Y-%m-%d")
		if self.mode_p == 'jours':
			"""
			delta = float(((d1 - d2).days+1)/30.0)
			#if int(d1.month) == 01 or int(d1.month) == 03 or int(d1.month) == 05 or int(d1.month) == 07 or int(d1.month) == 08 or int(d1.month) == 10 or int(d1.month) == 12:
			if  abs((d1-d2).days) == 30:
				delta = float(((d1 - d2).days)/30.0)
			#exceotion pour mois février
			if int(d1.month) == 02 and int(d2.month) == 02 and abs((d1-d2).days) == 28:
				delta = float(((d1 - d2).days+2)/30.0)
			if int(d1.month) == 02 and int(d2.month) == 02 and abs((d1-d2).days) == 27:
				delta = float(((d1 - d2).days+3)/30.0)

			if (int(d1.month) - int(d2.month)) == 3 and abs((d1-d2).days) == 91 or abs((d1-d2).days) == 92:
				delta = 90/30.0

			if  ( abs((d1-d2).days) == 107 or abs((d1-d2).days) == 106 ) and ( (int(d1.month) - int(d2.month)) == 3 or (int(d1.month) - int(d2.month)) == 4 ):
				delta = 105/30.0
			"""
		if self.mode_p == 'mois':
			delta = d1.month - d2.month
		if d1 > d2 :
			nb_mois = float((d1.year - d2.year)*12) + delta
		self.nb_mois = nb_mois
		return nb_mois
	nb_mois = fields.Float(compute='get_total_mois')

	@api.one
	@api.depends('solde_jour','somme_options','unit','nb_seance','fin','debut','tarif_garderier','nb_jour_garderier','remise','tarif_scholar')
	def on_change_tarif_a_payer(self):
		#a = 0.0
		if self.mode_p == 'mois':
			if self.abonnement_id.garderier:
				a_one__month =self.tarif_abonnement
				nb_mois = self.get_total_mois(self.debut,self.fin)
				self.tarif_a_payer = (self._get_total_options()+ a_one__month*nb_mois + self.abonnement_id.tarif_garderier * nb_mois )
				#a =  self._get_total_options()+ a_one__month*nb_mois + self.abonnement_id.tarif_garderier * nb_mois - self.remise
			else:
				a_one__month =self.tarif_abonnement
				nb_mois = self.get_total_mois(self.debut,self.fin)
				self.tarif_a_payer = (self._get_total_options()+ a_one__month*nb_mois + (self.tarif_garderier * self.nb_jour_garderier) )


				#a =  (self._get_total_options()+ a_one__month*nb_mois + (self.tarif_garderier * self.nb_jour_garderier)) - self.remise

		elif self.mode_p == 'jours':

			if self.abonnement_id.garderier:
				a_one__month =self.tarif_abonnement
				nb_mois = float(self.solde_jour/30.0)
				self.tarif_a_payer = (self._get_total_options()+ a_one__month*nb_mois + (self.abonnement_id.tarif_garderier * nb_mois) )

				#a =  (self._get_total_options()+ a_one__month*nb_mois + (self.abonnement_id.tarif_garderier * nb_mois) + self.abonnement_id.tarif_scholar ) - self.remise
			else:
				a_one__month =self.tarif_abonnement
				nb_mois = float(self.solde_jour)/30.0
				self.tarif_a_payer = ( self._get_total_options()+ a_one__month*nb_mois + (self.tarif_garderier * self.nb_jour_garderier) )
				#a =  (self._get_total_options()+ a_one__month*nb_mois + (self.tarif_garderier * self.nb_jour_garderier) + self.abonnement_id.tarif_scholar ) - self.remise

		else:
			self.tarif_a_payer = self._get_total_options()+(self.unit*self.nb_seance)
			#a = self._get_total_options()+(self.unit*self.nb_seance)

		if self.scholar:
			self.tarif_a_payer += self.tarif_scholar

		if self.add_remise:
			self.tarif_a_payer -= self.remise	


		return self.tarif_a_payer




	@api.multi
	def get_adherent_contrat(self):
		gym_ids = self._context.get('active_ids', [])
		gym_adh = self.env[('gym.adherent')].browse(gym_ids)
		return gym_adh

	@api.one
	@api.onchange('adherent')
	def onchange_contrat(self):
		self.abonnement_id = self.adherent.abonnement_id.id
		return self.abonnement_id.id

	@api.one
	@api.onchange('adherent','solde_jour')
	def onchange_abonement_remise(self):
		if self.adherent.abonnement_id.remise:
			self.add_remise = True
			self.remise = self.adherent.abonnement_id.taux_remise * float(self.solde_jour)/30.0
			return self.abonnement_id.taux_remise * float(self.solde_jour)/30.0


	"""Aqui hay los campos del clase //segunda lista"""

	abonnement_id = fields.Many2one('gym.abonnement','Abonnement', default= get_default_abonnement_id)
	tarif_a_payer = fields.Float('Tarif a payer',compute='on_change_tarif_a_payer',readonly=False,store=True,track_visibility='always')
	adherent = fields.Many2one('gym.adherent','Adherent',default=get_adherent_contrat, store=True)

	reste_a_payer = fields.Float('Reste a payer',store=True,readonly=False)
	net_payee = fields.Float('Net payé',track_visibility='always')
	"""Fin declaracion de los campos"""

	@api.multi
	@api.depends('net_payee')
	def get_amount_letter(self):
		amount = convertion.trad(self.net_payee,'Dinar')
		return amount


	@api.one
	@api.onchange('tarif_a_payer')
	def onchange_total_payer(self):
		self.net_payee = self.tarif_a_payer
		return self.net_payee

	@api.multi
	def open_record(self):
			rec_id = self.id
			form_id = self.env.ref('gestion_adherent.view_paieabonn_compute_wizard_history_2')

			return {
					'type': 'ir.actions.act_window',
					'name': 'Historique des paiements',
					'res_model': 'paiement.abonnement',
					'res_id': rec_id,
					'view_type': 'form',
					'view_mode': 'form',
					'view_id': form_id.id,
					'context': {},           
					#'flags': {'initial_mode': 'edit'},
					'target': 'current',
				}

	#la funcion principal para añadir los dias pagados a la suscripcion despues el pago
	@api.multi
	def paye_abonnement(self,context=None):

			gym_ids = context.get('active_ids', [])
			gym_adh = self.env[('gym.adherent')]

			for record in gym_adh.browse(gym_ids):
				if self.debut and self.fin:
					record.abonnement_id.debut = self.debut
					record.abonnement_id.jusqua = self.fin
					#record.solde = abs(self.fin - self.debut)
					record.date=self.fin

	#abreviacion de los meses
	def get_month_letter(self):
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
		return mois_en_lettre

	#para añadir una sequencia a cada pago despues la creacion del record
	@api.model
	def create(self,vals):
		sequence=self.env[('ir.sequence')].get('reg_code_paie')
		ref = sequence+'-'+self.get_month_letter()+'-'+str((date.today()).year-2000)
		vals['name']=ref
		rec = super(paiement_abonnement, self).create(vals)

		##
		id_ab = int(vals['abonnement_id'])
		id_child = int(vals['adherent'])
		abonnement_id = self.env['gym.abonnement'].browse(id_ab)
		child = self.env['gym.adherent'].browse(id_child)
		abonnement_id.update({'jusqua':vals['fin'],'debut':vals['debut'],'mode_p':vals['mode_p']})
		if vals['solde_jour']:
			abonnement_id.update({'solde_jour':vals['solde_jour']})
		child.update({'date':vals['fin']})
		##
		if vals['tarif_a_payer'] == 0.0:
					raise osv.except_osv(
					_('Attention!'),
					_('La somme totale est égale a zéro !.'))

		if (vals['mode_p'] == 'mois' or vals['mode_p'] == 'jours') and not vals['adherent']:
					raise osv.except_osv(
					_('Attention!'),
					_('Veuillez ajouter un adhérent/un abonnement a ce paiement svp!.'))
		return rec




class gym_service(models.Model):
	_name = 'gym.service'
	_order='unit_mesure desc'


	name=fields.Char('Service')
	tarif= fields.Float('Tarif')
	unit_mesure = fields.Float('Unité')


class gym_option(models.Model):
	_name = 'gym.option'
	_order='quantite desc'


	name=fields.Char('Option')
	quantite=fields.Integer('Quantité')
	tarif= fields.Float('Tarif')


class gym_acheter_option(models.Model):
	_name = 'gym.acheter.option'
	_order='create_date desc'


	#recuperar el precio de cada producto
	@api.one
	@api.depends('quantite','option.tarif')
	def get_tarif(self):

		if self.quantite and self.option.tarif :
			self.somme = self.option.tarif*self.quantite

	#recuperar la quantidad disponible de un producto
	@api.onchange('option')
	def get_disponible_qty(self):
			self.qty_dispo = self.option.quantite

			

	qty_dispo = fields.Integer(string='Disponible',readonly=True)
	quantite=fields.Integer('Qty',default=1)
	option = fields.Many2one('gym.option','Produits')
	paiement_id = fields.Many2one('paiement.abonnement','Paiement')
	somme= fields.Float('Somme',compute='get_tarif',store='True')

	#para decrementar la quantidad de un producto despues la venta
	@api.model
	def create(self,vals):
		rec = super(gym_acheter_option, self).create(vals)

		option = vals['option']
		op = self.env['gym.option'].search([]).browse(option)
		if op.quantite - vals['quantite'] > 0:
				op.write({'quantite':op.quantite - vals['quantite']})
		else:
				raise osv.except_osv(
					_('Attention!'),
					_('Stock est insuffisant !.'))

		return rec



class gym_acheter_service(models.Model):
	_name = 'gym.acheter.service'
	_order='create_date desc'

	#recuperar el precio de un servicio
	@api.one
	@api.depends('duree','service.tarif')
	def get_tarif_service(self):

		if self.duree and self.service.tarif :
			self.somme_service = self.service.tarif*self.duree/self.service.unit_mesure

	duree = fields.Float('Durée')
	service = fields.Many2one('gym.service','Service')
	paiement_id = fields.Many2one('paiement.abonnement','Paiement')
	somme_service = fields.Float('Somme',compute='get_tarif_service',store='True')



class depense_depense(models.Model):
	_name = 'depense.depense'
	_order = 'date desc'

	name = fields.Char('Dépense')
	frais = fields.Float('Montant',required=True)
	date = fields.Date('Date',required=True)
	bloc = fields.Boolean('A ne pas compter')
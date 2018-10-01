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



class recette_recette(models.AbstractModel):
	_name = "recette.recette"

	_order='name desc'

	date_debut = fields.Date('Date debut')
	date_fin = fields.Date('Date fin',default=fields.Datetime.now)
	recette = fields.Float('Recettes',readonly=True)
	depense = fields.Float('Dépenses',readonly=True)
	benfice = fields.Float('Bénéfices',readonly=True)
	nombre_paiem = fields.Integer('Nombre de paiements effectuées',readonly=True)


	@api.one
	@api.onchange('date_debut','date_fin')
	def get_all_paiement_effectuee(self):
		cmpt = 0
		abonnement = self.env[('paiement.abonnement')].search([('create_date','>=',self.date_debut),('create_date','<=',self.date_fin)])
		for record in abonnement:	
			cmpt += 1
		self.nombre_paiem = cmpt
		return self.nombre_paiem

	###################################################################
	@api.one
	@api.onchange('date_debut','date_fin')
	def get_all_paiement(self):
		total_gain = 0.0
		abonnement = self.env[('paiement.abonnement')].search([('create_date','>=',self.date_debut),('create_date','<=',self.date_fin)])
		"""
		raise osv.except_osv(
						_('Attention!'),
						_(str(abonnement)))
		"""
		for record in abonnement:
				total_gain += record.net_payee
		self.recette = total_gain
		return total_gain
	###################################################################

	@api.one
	@api.onchange('date_debut','date_fin')
	def get_all_depense(self):
		total_dep = 0.0
		
		abonnement = self.env[('depense.depense')].search([('date','>=',self.date_debut),('date','<=',self.date_fin),('bloc','=',False)])
		"""
		raise osv.except_osv(
						_('Attention!'),
						_(str(abonnement)))
		"""
		for record in abonnement:
				total_dep += record.frais
		self.depense = total_dep
		return total_dep

	####################################################################
	@api.one
	@api.onchange('recette','depense')
	def get_all_benifice(self):
		total = 0.0 
		self.benfice = self.recette - self.depense
		return self.benfice
from direct.distributed.DistributedObject import DistributedObject

class DistributedGoofy(DistributedObject):
	""" THIS IS A DUMMY FILE FOR THE DISTRIBUTED CLASS"""

	def __init__(self, cr):
		DistributedObject.__init__(self, cr)

from collections import OrderedDict
import logging as log
from .book_price_q import BookPriceQ, IEXBookPriceQ


class Node:
	def __init__(self, data, prev = None, next = None):
		self.data = data
		self.next = next
		self.prev = prev
	
	def __repr__(self):
		return '<node  price:{}, lit:{}>'.format(self.data.price, self.data.lit)

class SortedIndexedDefaultList:
	'''
	This is an indexable, double-linked linked list with insertions coming always form iteration from the start.
	Delete: O(1)
	Insert: O(n) - but o(1) to put at front
	Read: : O(1)

	Retrieving a missing element will spur the creation of the element via the initialized.
	'''
	def __init__(self, index_func, initializer, index_multiplier = 1 ):
		self.start = None
		self.end = None
		self.index_func = index_func
		self.index_multiplier = index_multiplier
		self.index = {}
		self.initializer = initializer

	def __str__(self):
		return ',\n'.join([str(i) for i in self.ascending_items()])

	def insert(self, data):
		id = self.index_func(data)
		if id in self.index:
			raise KeyError
		else:
			n=Node(data = data)
			self.index[id] = n

			if self.start is None:	 #insert into linked list from start
				self.start = n
				self.end = n
				return n.data
			elif self.index_multiplier*self.index_func(self.start.data) > self.index_multiplier*id: #inserting at start
				self.start.prev = n
				n.next = self.start
				self.start = n
				return n.data
			else:
				current = self.start 
				while current.next is not None and self.index_multiplier*self.index_func(current.next.data) <= self.index_multiplier*id:
					current = current.next

				if current.next is None: #insert into end of linked list
					current.next = n
					n.prev = current
					self.end = n
					return current.next.data
				else:					#insert into middle of linked list
					n.next = current.next
					n.prev = current
					current.next.prev = n
					current.next = n
					return current.next.data

	def __contains__(self, index):
		return index in self.index

	def __getitem__(self, index):
		if index not in self.index:
			return self.insert(self.initializer(index))
		else:
			return self.index[index].data	

	def remove(self, index):
		try:
			node = self.index[index]
		except KeyError as e:
			log.debug('node at {} already removed'.format(index))
			return
		if node == self.start:
			self.start = node.next
		else:
			prev = node.prev
			prev.next = node.next

		if node == self.end:
			self.end = node.prev
		else:
			next = node.next
			next.prev = node.prev

		del self.index[index]

	def ascending_items(self):
		current = self.start
		while current is not None:
			yield current.data
			current = current.next

	def descending_items(self):
		current = self.end
		while current is not None:
			yield current.data
			current = current.prev

class IEXAskList(SortedIndexedDefaultList):

	def __init__(self):
		super().__init__(index_func=lambda bpq: ( bpq.price,  not bpq.lit), 
			initializer=lambda price, lit: IEXBookPriceQ(price, b'S', lit=lit))
	
	@staticmethod
	def adjust_index(index):
		price, lit = index
		adjusted_index = price, not lit
		return adjusted_index
	
	def __getitem__(self, index):
		adjusted_index = self.adjust_index(index)
		if adjusted_index not in self.index:
			price, lit = index
			return self.insert(self.initializer(price, lit=lit))
		else:
			return self.index[adjusted_index].data		
	
	def __contains__(self, index):
		booly = super().__contains__(self.adjust_index(index))
		return booly

	def remove(self, index):
		super().remove(self.adjust_index(index))

class IEXBidList(SortedIndexedDefaultList):

	def __init__(self):
		super().__init__(index_func=lambda bpq: ( - bpq.price, not bpq.lit), 
			initializer=lambda price, lit: IEXBookPriceQ(price, b'B', lit=lit))
		
	@staticmethod
	def adjust_index(index):
		price, lit = index
		adjusted_index =  - price, not lit
		return adjusted_index

	def __getitem__(self, index):
		adjusted_index = self.adjust_index(index)
		if adjusted_index not in self.index:
			price, lit = index
			return self.insert(self.initializer(price, lit=lit))
		else:		
			return self.index[adjusted_index].data	
	
	def __contains__(self, index):
		booly = super().__contains__(self.adjust_index(index))
		return booly

	def remove(self, index):
		super().remove(self.adjust_index(index))


if __name__ == '__main__':
	for l in IEXAskList(), IEXBidList():
		for price in (9, 11, 12 , 14):
			l.insert(IEXBookPriceQ(price, b'X'))
		l[(8, False)]
		for price in (9, 10, 12 , 14):
			l.insert(IEXBookPriceQ(price, b'X', lit=True))
		for each in l.ascending_items():
			print(each)
		print()
		l.remove((9, False))
		l.remove((12, False))
		l.remove((9, True))
		for each in l.ascending_items():
			print(each)
		print()
	

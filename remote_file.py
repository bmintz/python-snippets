import io
import requests
import typing

class RemoteFile(typing.BinaryIO):
	def __init__(self, url):
		self.url = url
		self.session = requests.Session()
		self._content_length = None
		self._if_range_header = None
		self.pos = 0

	def _fetch_content_length(self):
		r = self.session.head(self.url)
		self._set_if_range_header(r)
		self._content_length = int(r.headers['Content-Length'])

	def _set_if_range_header(self, r):
		if self._if_range_header is None:
			self._if_range_header = r.headers.get('ETag', r.headers.get('Last-Modified'))

	def read(self, size=-1):
		start = self.tell()
		end = '' if size == -1 else start + size - 1
		range_header = f'bytes={start}-{end}'

		headers = {'Range': range_header}
		if self._if_range_header is not None:
			headers['If-Range'] = self._if_range_header

		r = self.session.get(self.url, headers=headers)
		if r.status_code == 200:
			raise OSError('range requested but the whole file was returned')
		elif r.status_code == 416:
			raise OSError('requested range not satisfiable')
		elif r.status_code != 206:  # Partial content
			raise OSError('got unexpected status code', r.status_code)

		self._set_if_range_header(r)

		buf = r.content
		self.pos += len(buf)
		return buf

	def seek(self, offset, whence=io.SEEK_SET):
		old_pos = self.tell()

		if whence == io.SEEK_SET:
			if offset < 0:
				raise ValueError('negative seek value')
			self.pos = offset
		elif whence == io.SEEK_CUR:
			self.pos += offset
		elif whence == io.SEEK_END:
			if self._content_length is None:
				self._fetch_content_length()
			self.pos = self._content_length + offset

		if self.pos < 0:
			self.pos = old_pos
			raise OSError('new position would be negative')

		return self.pos

	def __repr__(self):
		return f'{type(self).__qualname__}({self.url!r})'

	def tell(self):
		return self.pos

	def writable(self):
		return False

	def seekable(self):
		return True

	def write(self):
		raise OSError('read only file')

	def truncate(self, size=None):
		raise OSError('read only file')

	def __enter__(self):
		return self

	def __exit__(self, *excinfo):
		self.session.close()

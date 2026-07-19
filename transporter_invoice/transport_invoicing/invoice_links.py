def set_if_has_field(doc, fieldname, value):
	if doc.meta.has_field(fieldname):
		doc.set(fieldname, value)

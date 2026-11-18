def test(kit, run):
    kit.add_fake_file('Paper A.pdf', kit.fake_pdf('Five forces shape competition in an industry.'))
    kit.add_fake_file('Paper B.pdf', kit.fake_pdf('Blue oceans are new markets without rivals.'))
    kit.add_fake_file('Broken.pdf', b'%PDF-1.4 not really a pdf')
    out = run(question='What are the main themes?')
    assert out['used'] == ['Paper A.pdf', 'Paper B.pdf'], out
    assert 'main themes' in out['reply']
    assert 'Broken.pdf' in out['reply']

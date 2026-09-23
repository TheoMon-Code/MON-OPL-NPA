#!/usr/bin/env python3
"""Strict-ish validator for the workbooks produced by MONXLSX.

LibreOffice opens files Excel refuses, so this checks the OOXML rules Excel is
known to enforce.  Every rule here exists because Excel rejects the file if it
is broken -- the activePane one is the rule that caused the first repair dialog.
"""
import sys, zipfile, posixpath, re
import xml.etree.ElementTree as ET

M  = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R  = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
CD = 'http://schemas.openxmlformats.org/drawingml/2006/chart'

errors, checks = [], []
def ok(msg):             checks.append(msg)
def bad(msg):            errors.append(msg)
def need(cond, msg):     ok(msg) if cond else bad(msg)

def colnum(ref):
    c = 0
    for ch in re.match(r'[A-Z]+', ref).group(0):
        c = c*26 + ord(ch)-64
    return c

def main(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()

    need(z.testzip() is None, 'zip integrity')

    for n in names:
        if n.endswith(('.xml', '.rels')):
            try: ET.fromstring(z.read(n))
            except Exception as e: bad('malformed XML in %s: %s' % (n, e))
    ok('all XML parts well-formed')

    # ── relationships resolve ────────────────────────────────────────────
    for n in [x for x in names if x.endswith('.rels')]:
        base = posixpath.dirname(posixpath.dirname(n))
        for rel in ET.fromstring(z.read(n)):
            t = rel.get('Target')
            if t.startswith('http'): continue
            p = posixpath.normpath(posixpath.join(base, t))
            if p not in names: bad('%s -> missing target %s' % (n, p))
    ok('all relationship targets resolve')

    # ── content types cover every part ───────────────────────────────────
    ct = ET.fromstring(z.read('[Content_Types].xml'))
    defaults  = {d.get('Extension').lower() for d in ct if d.tag.endswith('Default')}
    overrides = {o.get('PartName') for o in ct if o.tag.endswith('Override')}
    for n in names:
        if n == '[Content_Types].xml': continue
        if '/'+n not in overrides and n.rsplit('.', 1)[-1].lower() not in defaults:
            bad('no content type declared for %s' % n)
    ok('content types complete')

    # ── workbook: sheet order and defined names ─────────────────────────
    wb   = ET.fromstring(z.read('xl/workbook.xml'))
    rels = {r.get('Id'): r.get('Target')
            for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    sheets = []
    for sh in wb.find('{%s}sheets' % M):
        tgt = rels[sh.get('{%s}id' % R)]
        sheets.append((sh.get('name'), posixpath.normpath('xl/'+tgt)))
    ok('%d sheets: %s' % (len(sheets), ', '.join(s[0] for s in sheets)))

    dn = wb.find('{%s}definedNames' % M)
    if dn is not None:
        for d in dn:
            lsi = d.get('localSheetId')
            if lsi is not None and not (0 <= int(lsi) < len(sheets)):
                bad('definedName localSheetId out of range: %s' % lsi)
            ref = (d.text or '')
            for part in ref.split(','):
                nm = part.split('!')[0].strip("'")
                if nm and nm not in [s[0] for s in sheets]:
                    bad('definedName points at unknown sheet %r' % nm)
        ok('%d defined name(s) valid' % len(dn))

    # ── styles: every s="N" must exist ──────────────────────────────────
    st  = ET.fromstring(z.read('xl/styles.xml'))
    nxf = len(st.find('{%s}cellXfs' % M))
    fonts   = len(st.find('{%s}fonts' % M))
    fills   = len(st.find('{%s}fills' % M))
    borders = len(st.find('{%s}borders' % M))
    for xf in st.find('{%s}cellXfs' % M):
        for attr, cnt, label in (('fontId', fonts, 'font'), ('fillId', fills, 'fill'),
                                 ('borderId', borders, 'border')):
            v = int(xf.get(attr, 0))
            if v >= cnt: bad('cellXf references %s %d but only %d declared' % (label, v, cnt))
    need(fills >= 2, 'fills 0 and 1 reserved (none + gray125)')
    ok('styles consistent (%d xfs, %d fonts, %d fills, %d borders)' % (nxf, fonts, fills, borders))

    # ── per sheet ───────────────────────────────────────────────────────
    sheet_numbers = {}
    for name, part in sheets:
        ws = ET.fromstring(z.read(part))
        tag = lambda p, t: p.find('{%s}%s' % (M, t))

        # element order matters to Excel
        order = ['sheetPr', 'dimension', 'sheetViews', 'sheetFormatPr', 'cols', 'sheetData',
                 'sheetCalcPr', 'sheetProtection', 'autoFilter', 'mergeCells',
                 'conditionalFormatting', 'dataValidations', 'hyperlinks', 'printOptions',
                 'pageMargins', 'pageSetup', 'headerFooter', 'drawing']
        seen, last = [], -1
        for child in ws:
            t = child.tag.split('}')[1]
            if t in order:
                idx = order.index(t)
                if idx < last: bad('%s: <%s> out of schema order' % (name, t))
                last = idx
                seen.append(t)

        # THE pane rule
        for pane in ws.iter('{%s}pane' % M):
            xs, ys = pane.get('xSplit'), pane.get('ySplit')
            want = 'bottomRight' if (xs and ys) else ('bottomLeft' if ys else 'topRight')
            got  = pane.get('activePane')
            need(got == want,
                 '%s: pane xSplit=%s ySplit=%s -> activePane=%s' % (name, xs, ys, got))
            for sel in ws.iter('{%s}selection' % M):
                if sel.get('pane') and sel.get('pane') != want:
                    bad('%s: <selection pane="%s"> does not match the pane' % (name, sel.get('pane')))

        # cell references consistent with their row, ascending, styles in range
        maxrow = maxcol = 0
        numeric_cells = {}
        sd = tag(ws, 'sheetData')
        for row in sd:
            rn = int(row.get('r'))
            maxrow = max(maxrow, rn)
            prev = 0
            for c in row:
                ref = c.get('r')
                if not ref.endswith(str(rn)):
                    bad('%s: cell %s sits in row %d' % (name, ref, rn)); continue
                cn = colnum(ref)
                if cn <= prev: bad('%s: cells not in ascending order at %s' % (name, ref))
                prev = cn
                maxcol = max(maxcol, cn)
                s = c.get('s')
                if s is not None and int(s) >= nxf:
                    bad('%s: cell %s uses style %s (only %d)' % (name, ref, s, nxf))
                t = c.get('t')
                v = c.find('{%s}v' % M)
                if t == 'inlineStr':
                    if c.find('{%s}is' % M) is None: bad('%s: %s inlineStr without <is>' % (name, ref))
                elif v is not None:
                    try: numeric_cells.setdefault(rn, {})[cn] = float(v.text)
                    except ValueError: bad('%s: %s typed numeric but value %r' % (name, ref, v.text))
        sheet_numbers[name] = numeric_cells

        dim = tag(ws, 'dimension').get('ref').split(':')[-1]
        need(colnum(dim) >= maxcol and int(re.search(r'\d+', dim).group(0)) >= maxrow,
             '%s: dimension %s covers the data' % (name, dim))

        mc = tag(ws, 'mergeCells')
        if mc is not None:
            need(int(mc.get('count')) == len(mc), '%s: mergeCells count matches' % name)

        af = tag(ws, 'autoFilter')
        if af is not None:
            end = af.get('ref').split(':')[-1]
            need(int(re.search(r'\d+', end).group(0)) <= maxrow,
                 '%s: autoFilter %s inside the data' % (name, af.get('ref')))

    # ── drawings and charts ─────────────────────────────────────────────
    for part in [n for n in names if n.startswith('xl/drawings/drawing')]:
        relp = 'xl/drawings/_rels/%s.rels' % posixpath.basename(part)
        drels = {r.get('Id') for r in ET.fromstring(z.read(relp))}
        d = ET.fromstring(z.read(part))
        used = set()
        for el in d.iter():
            for k, v in el.attrib.items():
                if k.endswith('}embed') or (k.endswith('}id') and R in k): used.add(v)
        for u in used:
            if u not in drels: bad('%s references %s which is not in its rels' % (part, u))
    ok('drawings reference only declared relationships')

    charts = [n for n in names if n.startswith('xl/charts/chart')]
    for part in charts:
        c = ET.fromstring(z.read(part))
        sers = list(c.iter('{%s}ser' % CD))
        need(len(sers) >= 1, '%s has %d series' % (posixpath.basename(part), len(sers)))
        for f in c.iter('{%s}f' % CD):
            m = re.match(r"'?([^'!]+)'?!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)", f.text or '')
            if not m: bad('%s: unreadable range %r' % (part, f.text)); continue
            sname, c1, r1, c2, r2 = m.group(1), m.group(2), int(m.group(3)), m.group(4), int(m.group(5))
            if sname not in [s[0] for s in sheets]:
                bad('%s: range points at unknown sheet %r' % (part, sname))
            elif int(r2) < int(r1):
                bad('%s: inverted range %s' % (part, f.text))
    ok('%d chart(s), all ranges resolve' % len(charts))

    # value series must actually contain numbers
    for part in charts:
        c = ET.fromstring(z.read(part))
        for val in c.iter('{%s}val' % CD):
            f = val.find('.//{%s}f' % CD)
            if f is None: continue
            m = re.match(r"'?([^'!]+)'?!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)", f.text)
            sname, col, r1, r2 = m.group(1), colnum(m.group(2)), int(m.group(3)), int(m.group(5))
            found = sum(1 for r in range(r1, r2+1)
                        if sheet_numbers.get(sname, {}).get(r, {}).get(col) is not None)
            need(found > 0, 'chart series %s holds %d numeric cells' % (f.text, found))

    print('\n'.join('  ok   ' + c for c in checks))
    if errors:
        print('\n'.join('  FAIL ' + e for e in errors))
        print('\n%d PROBLEM(S)' % len(errors)); return 1
    print('\nno problems found')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))

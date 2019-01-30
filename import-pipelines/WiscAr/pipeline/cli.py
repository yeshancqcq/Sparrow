from sys import exit
from os import environ, listdir, path
from datetime import datetime
from click import command, option, echo, secho, style
from labdata import Database
from labdata.database import get_or_create

from  .extract_tables import extract_data_tables

def print_dataframe(df):
    secho(str(df.fillna(''))+'\n', dim=True)

def extract_analysis(db, fn, verbose=False):
    # Extract data tables from Excel sheet

    # File modification time is right now the best proxy
    # for creation date (note: sessions will be duplicated
    # if input files are changed)
    mod_time = datetime.fromtimestamp(path.getmtime(fn))

    incremental_heating, info, results = extract_data_tables(fn)
    if verbose:
        print_dataframe(incremental_heating)
        print_dataframe(info)
    print_dataframe(results.transpose())

    cls = db.mapped_classes

    def get(c, **kwargs):
        return get_or_create(db.session, c, **kwargs)

    def get_error_metric(label):
        error_metric = label.replace("± ","")
        description = ""
        if error_metric == '1s':
            description = "1 standard deviation"
        elif error_metric == '2s':
            description = "2 standard deviations"
        return get(cls.error_metric, id=error_metric,
                    description=description)

    project = get(cls.project,id=info.pop('Project'))
    project.title = project.id
    sample = get(cls.sample,
        id=info.pop('Sample'))
    sample.project = project.id
    db.session.add(sample)
    target = get(cls.material, id=info.pop('Material'))

    instrument = get(cls.instrument,
        name="MAP 215-50")

    method = get(cls.method,
        id="Ar/Ar "+info.pop("Type"))

    session = get(cls.session,
        sample_id=sample.id,
        date=mod_time,
        instrument=instrument.id,
        technique=method.id,
        target=target.id)
    session.data = info.to_dict()
    db.session.add(session)

    get(cls.error_metric,
        id='1s', description='1 standard deviation',
        authority='WiscAr')

    param_data = {
        'Tstep': "Temperature of heating step",
        'power': "Laser power of heating step",
        '36Ar(a)': "36Ar, reactor corrected for air interference",
        '37Ar(ca)': "37Ar, reactor corrected for Ca interference",
        '38Ar(cl)': "38Ar, reactor corrected for Cl interference",
        '39Ar(k)': "39Ar, corrected for amount produced by K",
        '40Ar(r)': "Radiogenic 40Ar measured abundance",
        'step_age': "Age calculated for a single heating step",
        '40Ar(r) [%]': "Radiogenic 40Ar, percent released in this step",
        '39Ar(k) [%]': "39Ar from potassium, percent released in this step",
        'K/Ca': "Potassium/Calcium ratio"
    }

    V = get(cls.unit, id='V', description='Measured isotope abundance',
            authority='WiscAr')
    percent = get(cls.unit, id='%')
    degrees_c = get(cls.unit, id="°C")
    Ma = get(cls.unit, id='Ma')
    ratio = get(cls.unit, id='ratio', authority="WiscAr")

    p = {}
    for k,v in param_data.items():
        p[k] = get(
            cls.parameter,
            id=k,
            authority="WiscAr")
        p[k].description = v
        db.session.add(p[k])

    def add_datum(analysis, **kwargs):
        dtype_cols = [i for i in
            cls.datum_type.__table__.columns.keys()
            if i != 'id']
        defaults = dict(
            is_computed=False,
            is_interpreted=False
        )
        dtype_kw = dict()
        for i in dtype_cols:
            val = kwargs.pop(i, defaults.get(i, None))
            if val is not None:
                dtype_kw[i] = val
        dtype = get(cls.datum_type, **dtype_kw)
        kwargs['type'] = dtype.id
        kwargs['analysis'] = analysis.id
        return get(cls.datum, **kwargs)


    i = 0
    for ix, row in incremental_heating.iterrows():
        analysis = get(cls.analysis,
            session_id=session.id,
            session_index=i,
            step_id=ix
        )
        analysis.in_plateau=row['in_plateau']
        analysis.is_interpreted = False
        db.session.add(analysis)
        i += 1

        def datum(**kwargs):
            return add_datum(analysis, **kwargs)

        # Check whether we are measuring laser power or temperature
        s = incremental_heating['temperature']
        if (s<=100).sum() == len(s):
            # Everything is less than 100
            datum(
                parameter=p['power'].id,
                unit=percent.id,
                description='Temperature of heating step',
                value=row['temperature'])
        else:
            datum(
                parameter=p['Tstep'].id,
                unit=degrees_c.id,
                description='Temperature of heating step',
                value=row['temperature'])

        for r in ['36Ar(a)','37Ar(ca)','38Ar(cl)','39Ar(k)',
                  '40Ar(r)','39Ar(k) [%]','40Ar(r) [%]']:
            unit = V
            if '[%]' in r:
                unit = percent
            datum(
                parameter=p[r].id, unit=unit.id,
                description=p[r].description,
                value=row[r])

        ix = list(row.index).index('Age')
        error_ix = ix+1
        em = get_error_metric(row.index[error_ix])

        datum(value=row['Age'],
            unit=Ma.id,
            parameter=p['step_age'].id,
            description="Age of heating step",
            error=row.iloc[error_ix],
            error_metric=em.id,
            error_unit=Ma.id)

        ix = list(row.index).index('K/Ca')
        error_ix = ix+1
        em = get_error_metric(row.index[error_ix])
        datum(value=row['K/Ca'],
            unit=ratio.id,
            parameter=p["K/Ca"].id,
            description="Potassium/Calcuim ratio",
            error=row.iloc[error_ix],
            error_metric=em.id,
            error_unit=ratio.id)

    db.session.commit()

@command(name="import-map")
@option('--stop-on-error', is_flag=True, default=False)
@option('--verbose','-v', is_flag=True, default=False)
def cli(stop_on_error=False, verbose=False):
    """
    Import WiscAr MAP spectrometer data (ArArCalc files) in bulk.
    """
    directory = environ.get("WISCAR_MAP_DATA")
    db = Database()

    for fn in listdir(directory):
        dn = path.join(directory, fn)
        if not path.isdir(dn): continue

        echo("Irradiation "+style(fn, bold=True))
        for fn in listdir(dn):
            if path.splitext(fn)[1] != '.xls': continue
            echo(fn)
            fp = path.join(dn, fn)
            try:
                extract_analysis(db, fp, verbose=verbose)
            except Exception as err:
                if stop_on_error: raise err
                secho(str(err), fg='red')
                echo("")

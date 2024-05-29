## Food Facilities Challenge

This project provides an HTTP API for retrieving mobile food facility
information from permit data retrieved from data.sfgov.org. There are
three API endpoints, each expecting a POST of a request entity of
content type `application/json`:

* `/by_applicant`
  Returns a list of mobile food facilities matching the provided
  vendor name (exactly), with entity format: `{"applicant": "J.R. Bob
  Dobbs"}` It accepts a `?status=` query parameter to retrieve only
  facilities with the provided status, out of `REQUESTED`, `EXPIRED`,
  `SUSPEND`, `APPROVED`, `ISSUED`.
  
* `/by_street`
  Returns a list of mobile food facilities matching the provided
  (partial) street name, with entity format: `{"name": "HAR"}`; this
  example would return facilities on `HARBOR ST` or `HARWELL CT` or
  `HARFOOT WALK`.
  
* `/by_location`
  Returns a list of the closest 5 facilities to the provided location,
  with entity format: `{"latitude": 37.76, "longitude": -122.4}`.  It
  accepts a `?only_approved=` query parameter, accepting truthy/falsey
  values (`0`|`1`, `true`|`false`, et al., defaults to true) to
  exclude or include facilities with status other than `APPROVED`.

Example `curl` commands for each are at the bottom of this document.

All of these endpoints return JSON representations of the full
facility permit record from the original dataset; fields of particular
interest include `Address`, `status`, `FoodItems`, and
`dayshours`--though not all records have values for some fields,
notably including those latter two.

## Architecture and Commentary

This service is built with [FastAPI](https://fastapi.tiangolo.com) and
[pandas](https://pandas.pydata.org).  The dataset is included
explicitly as `resources/Mobile_Food_Facility_Permit.csv` and is read
into memory as a pandas `DataFrame` at service startup. I started in
a Jupyter notebook using pandas to look at the dataset, experimented
with building the required queries there, and then just moved that
code into FastAPI path operation functions.

The code is in a single file. For a larger, more complicated problem I
would split the implementation into multiple modules--an obvious
starting division is one module for the HTTP API, one for dataset
access--but that division would be in the service of managing
complexity, whereas here I think it would be excess ceremony.

## Critique

### Style

For services with small inputs like this I generally like to have the
arguments as path or query parameters. However, since these names and
addresses often include non-URL-friendly characters like spaces and worse,
I put the primary arguments in JSON in the request body rather than
the worse alternative of URL-encoding the arguments. Once I got
started down that path I put the location latitude and longitude into 
the request body as well. It's possible I'd rather have those be path
parameters.

### Scaling/Performance

This implementation works because the dataset is tiny. Each request
needs to touch every row, but N=500. I suspect without evidence we
could scale this up 10, maybe even 100 times without the queries
getting slow.

At some sufficiently large N we'd need to get serious about query
performance, and I have a few approaches in mind. My usual first idea
is to move the dataset into a relational database, but I'm not sure
how much that buys us here: Applicant Name queries can be optimized,
but the Street Name (requiring a LIKE query) and, worst of all, the
Location query are just not going to see much improvement only from
moving to a database. (In ETL I'd make a new column of the street name
rather than deriving it fresh row by row for every query. That would
help a little.)

I suspect there's a standard technique for speeding up the street name
partial string search; maybe tables with a suitable index for the first
2 letters, first 3, and so on.  I'm not looking it up right now but
I'll bet that's a wheel not to reinvent.

The location query really does require a row-by-row search, for which
I think we'd want to partition space so as to reduce the number of
relevant rows. I haven't done anything like this so my first best idea
is naive: create some region centers, find the nearest 2 or 3 to the
query location, then only calculate distance to the facilities in
those few regions. I suspect this is also a solved problem (again not
looking it up right now) and another wheel not to reinvent.

For large enough N or heavy enough request volume I'd start thinking
about a different framework: Apache Spark comes to mind but (1) I'm
only familiar at the tutorial level and (2) I haven't thought it
through, much less done any experiments.

### Correctness

All of the testing here is happy path, and I'm doing very little to
ensure the input is reasonable. We get some checking for free from
FastAPI but I'm not even testing that. One cobwebby corner that comes
to mind: what happens if the request body content is an empty string?
A real service exposed to real end users would need more attention to
these details.

The permit dataset is a little messy and I haven't done much to fix
that, other than some flexibility in the (primitive) street name
extractor, and removing empty fields in the return values. Building a
real service would include some cleanup in ETL.

I started out thinking I was going to define pydantic classes for the
return values, and discovered that I'd have to implement the
conversion myself, or use the `pandas-to-pydantic` library, which
looks new enough that I could easily imagine spending two hours
wrestling with it only to throw up my hands and write my own converter
anyway. Discretion being the better part of valor, I bravely ran
away, and now just return the (almost) raw dicts. For production I'd
want to fix that.

The `by_applicant` endpoint feels incorrect, in that it requires an
exact match to the applicant field. You can get those from the
`by_location` or `by_street` endpoints, but I suspect we'd want
something more flexible for a real service.

## Installation

I'm using Python 3.12 and haven't been careful about version
compatibility, but I don't think I've done anything
cutting-edge. Given a reasonably modern Python (and I'd do this inside
a virtualenv because that's where I always start):

	pip install -r requirements.txt
	
then, to run the tests:

	pytest -v
	
or to run the server:

	fastapi dev app/api.py

Here are some queries I've run in testing:

	curl -H 'Content-Type: application/json' 'http://localhost:8000/by_applicant?status=APPROVED' --data '{"applicant":"Natan'\''s Catering"}'
	
	curl -H 'Content-Type: application/json' 'http://localhost:8000/by_street' --data '{"name":"HAY"}'
	
	curl -H 'Content-Type: application/json' 'http://localhost:8000/by_location' --data '{"latitude": 37.77, "longitude": -122.45}'

And, of course, there's the auto-generated API documentation at
`http://localhost:8000/redoc`.  The return values are undocumented because,
again, there's no trivial conversion from `DataFrame` to pydantic classes.

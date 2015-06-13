function rdf_array_to_table(rdf_array, rdf_prefixes) {

	if( Object.prototype.toString.call( rdf_array ) !== '[object Array]' )
	rdf_array = [];

	if( Object.prototype.toString.call( rdf_prefixes ) !== '[object Array]' )
	rdf_prefixes = [];

	// create elements <table> and a <tbody>
	var tbl     = document.createElement("table");
	var tblBody = document.createElement("tbody");

	// cells creation
	if(typeof rdf_prefixes == "undefined")
	rdf_prefixes = [];
	for(var i=0; i<rdf_prefixes.length; i++){
		// table row creation
		var row = document.createElement("tr");

		for(var j=0; j<rdf_prefixes[i].length; j++){
			// create element <td> and text node 
		        //Make text node the contents of <td> element
		        // put <td> at end of the table row
			var cell = document.createElement("td");
			//cannot submit @ character via hidden fields as in @prefix
			var at = "";
			if(j==0)
				at = "@";    
			var cellText = document.createTextNode(at+rdf_prefixes[i][j]); 

                	cell.appendChild(cellText);
                	row.appendChild(cell);
		}

		//trailing "." for turtle document
		var cell = document.createElement("td");
		var cellText = document.createTextNode(".");
                cell.appendChild(cellText);
                row.appendChild(cell);

		//row added to end of table body
		tblBody.appendChild(row);
	}

	for(var i=0; i<rdf_array.length; i++){
		// table row creation
		var row = document.createElement("tr");

		for(var j=0; j<rdf_array[i].length; j++){
			// create element <td> and text node 
		        //Make text node the contents of <td> element
		        // put <td> at end of the table row
			var cell = document.createElement("td");    
			var cellText = document.createTextNode(rdf_array[i][j]); 

                	cell.appendChild(cellText);
                	row.appendChild(cell);
		}

		//trailing "." for turtle document
		var cell = document.createElement("td");
		var cellText = document.createTextNode(".");
                cell.appendChild(cellText);
                row.appendChild(cell);

		//row added to end of table body
		tblBody.appendChild(row);
	}

        // append the <tbody> inside the <table>
        tbl.appendChild(tblBody);
 
        tbl.setAttribute("class", "rdf_table");
	return tbl;
}


//source: http://dbpedia.org/sparql?nsdecl
prefixes = {
"http://www.w3.org/2005/Atom": "a",
"http://schemas.talis.com/2005/address/schema#": "address",
"http://webns.net/mvcb/": "admin",
"http://atomowl.org/ontologies/atomrdf#": "atom",
"http://soap.amazon.com/": "aws",
"http://b3s.openlinksw.com/": "b3s",
"http://schemas.google.com/gdata/batch": "batch",
"http://purl.org/ontology/bibo/": "bibo",
"bif:": "bif",
"http://www.openlinksw.com/schemas/bugzilla#": "bugzilla",
"http://www.w3.org/2002/12/cal/icaltzd#": "c",
"http://dbpedia.org/resource/Category:": "category",
"http://www.crunchbase.com/": "cb",
"http://web.resource.org/cc/": "cc",
"http://purl.org/rss/1.0/modules/content/": "content",
"http://purl.org/captsolo/resume-rdf/0.2/cv#": "cv",
"http://purl.org/captsolo/resume-rdf/0.2/base#": "cvbase",
"http://www.ontologydesignpatterns.org/ont/d0.owl#": "d0",
"http://www.w3.org/2001/sw/DataAccess/tests/test-dawg#": "dawgt",
"http://dbpedia.org/resource/": "dbpedia",
"http://dbpedia.org/ontology/": "dbpedia-owl",
"http://dbpedia.org/property/": "dbpprop",
"http://purl.org/dc/elements/1.1/": "dc",
"http://purl.org/dc/terms/": "dcterms",
"http://digg.com/docs/diggrss/": "digg",
"http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#": "dul",
"urn:ebay:apis:eBLBaseComponents": "ebay",
"http://purl.oclc.org/net/rss_2.0/enc#": "enc",
"http://www.w3.org/2003/12/exif/ns/": "exif",
"http://api.facebook.com/1.0/": "fb",
"http://rdf.freebase.com/ns/": "fbase",
"http://api.friendfeed.com/2008/03": "ff",
"http://www.w3.org/2005/xpath-functions/#": "fn",
"http://xmlns.com/foaf/0.1/": "foaf",
"http://base.google.com/ns/1.0": "g",
"http://www.openlinksw.com/schemas/google-base#": "gb",
"http://schemas.google.com/g/2005": "gd",
"http://www.w3.org/2003/01/geo/wgs84_pos#": "geo",
"http://www.geonames.org/ontology#": "geonames",
"http://www.georss.org/georss": "georss",
"http://www.opengis.net/gml": "gml",
"http://purl.org/obo/owl/GO#": "go",
"http://www.georss.org/georss/": "grs",
"http://www.openlinksw.com/schemas/hlisting/": "hlisting",
"http://wwww.hoovers.com/": "hoovers",
"http:/www.purl.org/stuff/hrev#": "hrev",
"http://www.w3.org/2002/12/cal/ical#": "ical",
"http://web-semantics.org/ns/image-regions": "ir",
"http://www.itunes.com/DTDs/Podcast-1.0.dtd": "itunes",
"http://www.w3.org/ns/ldp#": "ldp",
"http://linkedgeodata.org/vocabulary#": "lgv",
"http://www.xbrl.org/2003/linkbase": "link",
"http://lod.openlinksw.com/": "lod",
"http://www.w3.org/2000/10/swap/math#": "math",
"http://search.yahoo.com/mrss/": "media",
"http://purl.org/commons/record/mesh/": "mesh",
"urn:oasis:names:tc:opendocument:xmlns:meta:1.0": "meta",
"http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#": "mf",
"http://musicbrainz.org/ns/mmd-1.0#": "mmd",
"http://purl.org/ontology/mo/": "mo",
"http://www.freebase.com/": "mql",
"http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#": "nci",
"http://www.semanticdesktop.org/ontologies/nfo/#": "nfo",
"http://www.openlinksw.com/schemas/ning#": "ng",
"http://www.nytimes.com/": "nyt",
"http://www.openarchives.org/OAI/2.0/": "oai",
"http://www.openarchives.org/OAI/2.0/oai_dc/": "oai_dc",
"http://www.geneontology.org/formats/oboInOwl#": "obo",
"urn:oasis:names:tc:opendocument:xmlns:office:1.0": "office",
"http://www.opengis.net/": "ogc",
"http://www.opengis.net/ont/gml#": "ogcgml",
"http://www.opengis.net/ont/geosparql#": "ogcgs",
"http://www.opengis.net/def/function/geosparql/": "ogcgsf",
"http://www.opengis.net/def/rule/geosparql/": "ogcgsr",
"http://www.opengis.net/ont/sf#": "ogcsf",
"urn:oasis:names:tc:opendocument:xmlns:meta:1.0:": "oo",
"http://a9.com/-/spec/opensearchrss/1.0/": "openSearch",
"http://sw.opencyc.org/2008/06/10/concept/": "opencyc",
"http://www.openlinksw.com/schema/attribution#": "opl",
"http://www.openlinksw.com/schemas/getsatisfaction/": "opl-gs",
"http://www.openlinksw.com/schemas/meetup/": "opl-meetup",
"http://www.openlinksw.com/schemas/xbrl/": "opl-xbrl",
"http://www.openlinksw.com/schemas/oplweb#": "oplweb",
"http://www.openarchives.org/ore/terms/": "ore",
"http://www.w3.org/2002/07/owl#": "owl",
"http://www.buy.com/rss/module/productV2/": "product",
"http://purl.org/science/protein/bysequence/": "protseq",
"http://www.w3.org/ns/prov#": "prov",
"http://backend.userland.com/rss2": "r",
"http://www.radiopop.co.uk/": "radio",
"http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
"http://www.w3.org/ns/rdfa#": "rdfa",
"http://www.openlinksw.com/virtrdf-data-formats#": "rdfdf",
"http://www.w3.org/2000/01/rdf-schema#": "rdfs",
"http://purl.org/stuff/rev#": "rev",
"http:/www.purl.org/stuff/rev#": "review",
"http://purl.org/rss/1.0/": "rss",
"http://purl.org/science/owl/sciencecommons/": "sc",
"http://purl.org/NET/scovo#": "scovo",
"http://www.w3.org/ns/sparql-service-description#": "sd",
"urn:sobject.enterprise.soap.sforce.com": "sf",
"http://rdfs.org/sioc/ns#": "sioc",
"http://rdfs.org/sioc/types#": "sioct",
"http://www.w3.org/2004/02/skos/core#": "skos",
"http://purl.org/rss/1.0/modules/slash/": "slash",
"sql:": "sql",
"http://xbrlontology.com/ontology/finance/stock_market#": "stock",
"http://www.openlinksw.com/schemas/twfy#": "twfy",
"http://umbel.org/umbel#": "umbel",
"http://umbel.org/umbel/ac/": "umbel-ac",
"http://umbel.org/umbel/sc/": "umbel-sc",
"http://purl.uniprot.org/": "uniprot",
"http://dbpedia.org/units/": "units",
"http://www.rdfabout.com/rdf/schema/uscensus/details/100pct/": "usc",
"http://www.openlinksw.com/xsltext/": "v",
"http://www.w3.org/2001/vcard-rdf/3.0#": "vcard",
"http://www.w3.org/2006/vcard/ns#": "vcard2006",
"http://www.openlinksw.com/virtuoso/xslt/": "vi",
"http://www.openlinksw.com/virtuoso/xslt": "virt",
"http://www.openlinksw.com/schemas/virtcxml#": "virtcxml",
"http://www.openlinksw.com/schemas/virtrdf#": "virtrdf",
"http://rdfs.org/ns/void#": "void",
"http://www.worldbank.org/": "wb",
"http://www.w3.org/2007/05/powder-s#": "wdrs",
"http://www.w3.org/2005/01/wf/flow#": "wf",
"http://wellformedweb.org/CommentAPI/": "wfw",
"http://dbpedia.openlinksw.com/wikicompany/": "wikicompany",
"http://www.wikidata.org/entity/": "wikidata",
"http://www.w3.org/2004/07/xpath-functions": "xf",
"http://gmpg.org/xfn/11#": "xfn",
"http://www.w3.org/1999/xhtml": "xhtml",
"http://www.w3.org/1999/xhtml/vocab#": "xhv",
"http://www.xbrl.org/2003/instance": "xi",
"http://www.w3.org/XML/1998/namespace": "xml",
"http://www.ning.com/atom/1.0": "xn",
"http://www.w3.org/2001/XMLSchema#": "xsd",
"http://www.w3.org/XSL/Transform/1.0": "xsl10",
"http://www.w3.org/1999/XSL/Transform": "xsl1999",
"http://www.w3.org/TR/WD-xsl": "xslwd",
"urn:yahoo:maps": "y",
"http://dbpedia.org/class/yago/": "yago",
"http://mpii.de/yago/resource/": "yago-res",
"http://gdata.youtube.com/schemas/2007": "yt",
"zem": "http://s.zemanta.com/ns#"
};

function replacePrefix(uri){
	var result = [uri, "none", "none"];
	$.each(prefixes, function(key, value){
		if(uri.indexOf(key) >- 1){
			result[0] = value + ":" + uri.replace(key, "");
			result[1] = value;
			result[2] = key;
			return;
		}
	return;
	});
	return result;
};

used_prefixes = [];


//takes uri and reflaces with prefix or otherwise surrounds with <>
function prefixise(href){
	var prefixed = replacePrefix(href);
	var result = "";
	if(prefixed[1]=="none"){
		result = "<"+href+">";
	}else{
		result = prefixed[0];


		// no duplicates
		var already_in = false;
		for(var k = 0 ; k < used_prefixes.length; k++){
			if(used_prefixes[k][1] == prefixed[1]+":"){
				already_in = true;
				break;
			}
		}

		if(already_in === false){
			used_prefixes.push(["prefix", prefixed[1] + ":", "<"+prefixed[2]+">"]);
		}
	}
	return result;
}


function shortenURI(uri, maxlength){
	if(uri.length <= maxlength)
		return uri;

	maxlength = maxlength -3; //because we include "..."

	var parts = uri.split("/");
	var head = parts[0];
	var tail = "";
	for(var i = 1; i <= (parts.length/2); i++){
		if((head.length + tail.length+parts[i].length + 1) >= maxlength)
			return head + "..." + tail;
		else 
			head += parts[i] + "/";
		if((head.length + tail.length + parts[parts.length-i] + 1)>=maxlength)
			return head + "..." + tail;
		else
			tail = "/" + parts[parts.length-i] + tail;
	}	
}
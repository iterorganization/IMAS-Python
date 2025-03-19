<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:yaslt="http://www.mod-xslt2.com/ns/1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" version="2.0" extension-element-prefixes="yaslt" xmlns:fn="http://www.w3.org/2005/02/xpath-functions" xmlns:local="http://www.example.com/functions/local" exclude-result-prefixes="local xs">
  <xsl:param name="DD_GIT_DESCRIBE" as="xs:string" required="yes"/>
  <xsl:param name="AL_GIT_DESCRIBE" as="xs:string" required="yes"/>
  <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
  <!-- This script transforms the IDSDef.xml file into an XML file which will be used to build the MDS+ tree-->
  <!-- It contains the full data structure and describes it in terms of MDS+ terminology (node, member) and types (TEXT,NUMERIC,SIGNAL)-->
  <!-- This XML file has then to be processed by the Java routine CompileTree to create the MDS+ tree (part of the MDS+ libraries) -->
  <!-- Time dependent numeric signals are of the SIGNAL type -->
  <!-- Time independent numeric signals are of the NUMERIC type -->
  <!-- Only Vector of strings (str_1d_type) are of the TEXT type --> <!-- Not sure the vector of strings with time-dependence will work with a TEXT declaration, though -->
  <!-- Written by F. Imbeaux -->

  <!-- Function for multiplying the number of descendents with timebasepath attribute by the occurrence of the child AoS -->
  <xsl:function name="local:count-dynamic-fields" as="xs:integer">
    <xsl:param name="current" as="node()"/>
    <xsl:param name="level" as="xs:integer"/>
    <xsl:param name="aos" as="xs:boolean"/>
    <xsl:value-of select="$current/@maxoccur*count($current//field[@type='dynamic' and (($aos and @data_type='struct_array') or (not($aos) and not(@data_type='struct_array'))) and count(ancestor::field[@data_type='struct_array'])=$level])+$current/@maxoccur*sum($current//field[@data_type='struct_array' and not(@maxoccur='unbounded') and count(ancestor::field[@data_type='struct_array'])=$level]/local:count-dynamic-fields(.,$level+1,$aos))"/>
  </xsl:function>

  <!-- Scan for top-level elements -->
  <xsl:template match = "/*">
    <tree>
      <member NAME="REF_INFO" USAGE="NUMERIC"/>
      <node NAME="VERSION">
        <member NAME="DATA_DICT" USAGE="TEXT"><data>"<xsl:value-of select="$DD_GIT_DESCRIBE"/>"</data></member>
        <member NAME="ACC_LAYER" USAGE="TEXT"><data>"<xsl:value-of select="$AL_GIT_DESCRIBE"/>"</data></member>
        <member NAME="BACK_MAJOR" USAGE="NUMERIC"></member>
        <member NAME="BACK_MINOR" USAGE="NUMERIC"></member>
      </node>

      <xsl:apply-templates select = "IDS"/>
    </tree>
  </xsl:template>



  <!-- First, we scan at the IDS level -->
  <xsl:template match = "IDS">
    <node>
      <xsl:attribute name="NAME"><xsl:value-of select="@name"/></xsl:attribute>
      <xsl:apply-templates select = "field"/>

      <!-- Create subtrees for IDS occurrence. If parameter maxoccur is not defined, 10 additional occurrences are created-->
      <xsl:call-template name = "addOccurrence" >
        <xsl:with-param name = "iteration" select = "if (@maxoccur) then @maxoccur else 10" />
      </xsl:call-template>

    </node>
  </xsl:template>



  <!-- Then we scan the fields recursively -->
  <xsl:template match = "field">
    <xsl:choose>
      <xsl:when test="@data_type='structure'">
        <!-- this is a structure : write as node and scan the child elements recursively -->
        <node>
          <xsl:attribute name="NAME"><xsl:value-of select="@name"/></xsl:attribute>

          <xsl:apply-templates select = "field"/>
        </node>
      </xsl:when>
      <xsl:when test="@data_type='struct_array'">
	<node>
          <xsl:attribute name="NAME"><xsl:value-of select="@name"/></xsl:attribute>
	  <member>
	    <xsl:attribute name="NAME">static</xsl:attribute>
	    <xsl:attribute name="USAGE">NUMERIC</xsl:attribute>
	  </member>
	  <node>
	    <xsl:attribute name="NAME">timed_aos</xsl:attribute>
	    <xsl:call-template name = "makeAosSubtrees" >
	      <xsl:with-param name = "instances" select = "if (@type='dynamic') then 1 else local:count-dynamic-fields(.,1,true())" />
	    </xsl:call-template>
	  </node>
	  <node>
	    <xsl:attribute name="NAME">timed_data</xsl:attribute>
	    <xsl:call-template name = "makeDataSubtrees" >
		  <xsl:with-param name = "instances" select = "if (@type='dynamic') then 0 else local:count-dynamic-fields(.,1,false())"/>
	    </xsl:call-template>
	  </node>
    </node>
      </xsl:when>
      <xsl:otherwise>
        <!-- this is a bottom element -->
        <member>
          <xsl:attribute name="NAME"><xsl:value-of select="@name"/></xsl:attribute>
	  <!-- There used to be an instruction to use NUMERIC for dynamic str_1d_type fields, not sure if this was on purpose or some mis-use of logical operator precedence -->
          <xsl:attribute name="USAGE"><xsl:value-of select="if(@type='dynamic') then 'SIGNAL' else 'NUMERIC'"/></xsl:attribute>
      </member></xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  
  <!-- Additional IDS occurrence creation -->
  <xsl:template name="addOccurrence">
    <xsl:param name="iteration"/>
    <xsl:variable name="current" select="."/>
    <xsl:for-each select="1 to $iteration">
      <node>
        <xsl:attribute name="NAME">
          <xsl:value-of select="."/>
        </xsl:attribute>
        <xsl:apply-templates select = "$current/field"/>
      </node>
    </xsl:for-each>
  </xsl:template>

  
  <!-- Aos timed node creation: Aos childs-->
  <xsl:template name="makeAosSubtrees">
    <xsl:param name="instances" select="100"/>
    <xsl:for-each select="1 to xs:integer(1+(($instances - 1) div 1000))">
      <xsl:variable name="group" select="."/>
      <node>
        <xsl:attribute name="NAME"><xsl:value-of select="concat('group_',.)"/></xsl:attribute>
	<xsl:for-each select="1 to 1000">
	  <xsl:variable name="item" select="($group - 1) * 1000 + ."/>
	  <xsl:if test="$item &lt;= $instances">
	    <node>
              <xsl:attribute name="NAME"><xsl:value-of select="concat('item_',.)"/></xsl:attribute>
	      <member>
		<xsl:attribute name="NAME">aos</xsl:attribute>
		<xsl:attribute name="USAGE">NUMERIC</xsl:attribute>
	      </member>
	      <member>
		<xsl:attribute name="NAME">time</xsl:attribute>
		<xsl:attribute name="USAGE">NUMERIC</xsl:attribute>
	      </member>
	    </node>
	  </xsl:if>
	</xsl:for-each>
      </node>
    </xsl:for-each>
  </xsl:template>

  
  <!-- Aos timed node creation: Data childs -->
  <xsl:template name="makeDataSubtrees">
    <xsl:param name="instances"/>
    <xsl:for-each select="1 to xs:integer(1+(($instances - 1) div 1000))">
      <xsl:variable name="group" select="."/>
      <node>
        <xsl:attribute name="NAME"><xsl:value-of select="concat('group_',.)"/></xsl:attribute>
	<xsl:for-each select="1 to 1000">
	  <xsl:variable name="item" select="($group - 1) * 1000 + ."/>
	  <xsl:if test="$item &lt;= $instances">
	    <member>
              <xsl:attribute name="NAME"><xsl:value-of select="concat('item_',$item)"/></xsl:attribute>
              <xsl:attribute name="USAGE">NUMERIC</xsl:attribute>
            </member>
	  </xsl:if>
	</xsl:for-each>
      </node>
    </xsl:for-each>
  </xsl:template>

</xsl:stylesheet>

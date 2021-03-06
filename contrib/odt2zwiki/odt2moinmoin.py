#!/usr/bin/python

"""
            import pdb; pdb.set_trace()
odt2moinmoin
=======

odt2moinmoin converts files in Open Document Text format (ODT) into
ZWiki MoinMoin-formatted plain text.

Written by by [Yuri Takhteyev](http://www.freewisdom.org).

Project website: http://www.freewisdom.org/projects/odt2txt/
Contact: yuri [at] freewisdom.org

License: GPL 2 (http://www.gnu.org/copyleft/gpl.html) or BSD

Version: 0.1 (April 7, 2006)

"""



import sys, zipfile, xml.dom.minidom
from odf.namespaces import nsdict
from odf.elementtypes import *

IGNORED_TAGS = [
    'draw:a'
    'draw:g',
    'draw:line',
    'draw:object-ole',
    'office:annotation',
    'svg:desc',
] + [ nsdict[item[0]]+":"+item[1] for item in empty_elements]

INLINE_TAGS = [ nsdict[item[0]]+":"+item[1] for item in inline_elements]

FOOTNOTE_STYLES = ["Footnote"]


class TextProps:
    """ Holds properties for a text style. """

    def __init__ (self):

        self.italic = False
        self.bold = False
        self.fixed = False
        self.underlined = False

    def setItalic (self, value):
        if value == "italic":
            self.italic = True

    def setBold (self, value):
        if value == "bold":
            self.bold = True

    def setFixed (self, value):
        self.fixed = value

    def __str__ (self):

        return "[i=%s, h=i%s, fixed=%s]" % (str(self.italic),
                                          str(self.bold),
                                          str(self.fixed))

class ParagraphProps:
    """ Holds properties of a paragraph style. """

    def __init__ (self):

        self.blockquote = False
        self.headingLevel = 0
        self.code = False
        self.title = False
        self.indented = 0

    def setIndented (self, value):
        self.indented = value

    def setHeading (self, level):
        self.headingLevel = level

    def setTitle (self, value):
        self.title = value

    def setCode (self, value):
        self.code = value


    def __str__ (self):

        return "[bq=%s, h=%d, code=%s]" % (str(self.blockquote),
                                           self.headingLevel,
                                           str(self.code))


class ListProperties:
    """ Holds properties for a list style. """

    def __init__ (self):
        self.ordered = False

    def setOrdered (self, value):
        self.ordered = value



class OpenDocumentTextFile:


    def __init__ (self, filepath):
        self.footnotes = []
        self.footnoteCounter = 0
        self.textStyles = {"Standard": TextProps()}
        self.paragraphStyles = {"Standard": ParagraphProps()}
        self.listStyles = {}
        self.fixedFonts = []
        self.hasTitle = 0
        self.baseURL = "BaseURL"

        self.load(filepath)


    def processFontDeclarations (self, fontDecl):
        """ Extracts necessary font information from a font-declaration
            element.
            """
        for fontFace in fontDecl.getElementsByTagName("style:font-face"):
            if fontFace.getAttribute("style:font-pitch") == "fixed":
                self.fixedFonts.append(fontFace.getAttribute("style:name"))



    def extractTextProperties (self, style, parent=None):
        """ Extracts text properties from a style element. """

        textProps = TextProps()

        if parent:
            parentProp = self.textStyles.get(parent, None)
            if parentProp:
                textProp = parentProp

        textPropEl = style.getElementsByTagName("style:text-properties")
        if not textPropEl: return textProps

        textPropEl = textPropEl[0]

        italic = textPropEl.getAttribute("fo:font-style")
        bold = textPropEl.getAttribute("fo:font-weight")

        textProps.setItalic(italic)
        textProps.setBold(bold)

        if textPropEl.getAttribute("style:font-name") in self.fixedFonts:
            textProps.setFixed(True)

        return textProps

    def extractParagraphProperties (self, style, parent=None):
        """ Extracts paragraph properties from a style element. """

        paraProps = ParagraphProps()

        name = style.getAttribute("style:name")

        if name.startswith("Heading_20_"):
            level = name[11:]
            try:
                level = int(level)
                paraProps.setHeading(level)
            except:
                level = 0

        if name == "Title":
            paraProps.setTitle(True)

        paraPropEl = style.getElementsByTagName("style:paragraph-properties")
        if paraPropEl:
            paraPropEl = paraPropEl[0]
            leftMargin = paraPropEl.getAttribute("fo:margin-left")
            if leftMargin:
                try:
                    leftMargin = float(leftMargin[:-2])
                    if leftMargin > 0.01:
                        paraProps.setIndented(True)
                except:
                    pass

        textProps = self.extractTextProperties(style)
        if textProps.fixed:
            paraProps.setCode(True)

        return paraProps


    def processStyles(self, styleElements):
        """ Runs through "style" elements extracting necessary information.
            """

        for style in styleElements:

            name = style.getAttribute("style:name")

            if name == "Standard": continue

            family = style.getAttribute("style:family")
            parent = style.getAttribute("style:parent-style-name")

            if family == "text":
                self.textStyles[name] = self.extractTextProperties(style,
                                                                   parent)

            elif family == "paragraph":
                self.paragraphStyles[name] = (
                                 self.extractParagraphProperties(style,
                                                                 parent))
    def processListStyles (self, listStyleElements):

        for style in listStyleElements:
            name = style.getAttribute("style:name")

            prop = ListProperties()
            if style.childNodes:
                if ( style.childNodes[0].tagName
                     == "text:list-level-style-number" ):
                    prop.setOrdered(True)

            self.listStyles[name] = prop


    def load(self, filepath):
        """ Loads an ODT file. """

        zip = zipfile.ZipFile(filepath)

        styles_doc = xml.dom.minidom.parseString(zip.read("styles.xml"))
        self.processFontDeclarations(styles_doc.getElementsByTagName(
            "office:font-face-decls")[0])
        self.processStyles(styles_doc.getElementsByTagName("style:style"))
        self.processListStyles(styles_doc.getElementsByTagName(
            "text:list-style"))

        self.content = xml.dom.minidom.parseString(zip.read("content.xml"))
        self.processFontDeclarations(self.content.getElementsByTagName(
            "office:font-face-decls")[0])
        self.processStyles(self.content.getElementsByTagName("style:style"))
        self.processListStyles(self.content.getElementsByTagName(
            "text:list-style"))

    def compressCodeBlocks(self, text):
        """ Removes extra blank lines from code blocks. """

        lines = text.split("\n")
        buffer = []
        numLines = len(lines)
        for i in range(numLines):

            if (lines[i].strip() or i == numLines-1  or i == 0 or
                not ( lines[i-1].startswith("    ")
                      and lines[i+1].startswith("    ") ) ):
                buffer.append("\n" + lines[i])

        return ''.join(buffer)


    def listToString (self, listElement, indent = 0):

        buffer = []

        styleName = listElement.getAttribute("text:style-name")
        props = self.listStyles.get(styleName, ListProperties())

        i = 0
        for item in listElement.childNodes:
            buffer.append(" "*indent)
            i += 1
            if props.ordered:
                number = str(i)
                number = " " + number + ". "
                buffer.append(" 1. ")
            else:
                buffer.append(" * ")
            subitems = [el for el in item.childNodes
                          if el.tagName in ["text:p", "text:h", "text:list"]]
            for subitem in subitems:
                if subitem.tagName == "text:list":
                    buffer.append("\n")
                    buffer.append(self.listToString(subitem, indent+3))
                else:
                    buffer.append(self.paragraphToString(subitem, indent+3))
            buffer.append("\n")

        return ''.join(buffer)

    def tableToString (self, tableElement):
        """ MoinMoin used || to delimit table cells
        """

        buffer = []

        for item in tableElement.childNodes:
            if item.tagName == "table:table-header-rows":
                buffer.append(self.tableToString(item))
            if item.tagName == "table:table-row":
                buffer.append("\n||")
                for cell in item.childNodes:
                    buffer.append(self.paragraphToString(cell))
                    buffer.append("||")
        return ''.join(buffer)


    def toString (self):
        """ Converts the document to a string. """
        body = self.content.getElementsByTagName("office:body")[0]
        text = body.childNodes[0]

        buffer = []

        paragraphs = [el for el in text.childNodes
                      if el.tagName in ["text:p", "text:h","text:section",
                                        "text:list", "table:table"]]

        for paragraph in paragraphs:
            if paragraph.tagName == "text:list":
                text = self.listToString(paragraph)
            elif paragraph.tagName == "text:section":
                text = self.textToString(paragraph)
            elif paragraph.tagName == "table:table":
                text = self.tableToString(paragraph)
            else:
                text = self.paragraphToString(paragraph)
            if text:
                buffer.append(text)

        if self.footnotes:

            buffer.append("----")
            for cite, body in self.footnotes:
                buffer.append("%s: %s" % (cite, body))


        buffer.append("")
        return self.compressCodeBlocks('\n\n'.join(buffer))


    def textToString(self, element):

        buffer = []

        for node in element.childNodes:

            if node.nodeType == xml.dom.Node.TEXT_NODE:
                buffer.append(node.nodeValue)

            elif node.nodeType == xml.dom.Node.ELEMENT_NODE:
                tag = node.tagName

                if tag == "text:note":
                    cite = (node.getElementsByTagName("text:note-citation")[0]
                                .childNodes[0].nodeValue)

                    body = (node.getElementsByTagName("text:note-body")[0]
                                .childNodes[0])

                    self.footnotes.append((cite, self.textToString(body)))

                    buffer.append("^%s^" % cite)

                elif tag == "text:s":
                    try:
                        num = int(node.getAttribute("text:c"))
                        buffer.append(" "*num)
                    except:
                        buffer.append(" ")

                elif tag == "text:tab":
                    buffer.append("    ")


                elif tag == "text:a":

                    text = self.textToString(node)
                    link = node.getAttribute("xlink:href")
                    if link.strip() == text.strip():
                        buffer.append("[%s] " % link.strip())
                    else:
                        buffer.append("[%s %s] " % (link.strip(), text.strip()))

                elif tag == "draw:image":
                    link = node.getAttribute("xlink:href")
                    if link and link[:2] == './': # Indicates a sub-object, which isn't supported
                        continue
                    if link and link[:9] == 'Pictures/':
                        link = self.baseURL + "/" + link[9:]
                    buffer.append("%s\n" % link)

                elif tag == "text:line-break":
                    buffer.append("\n")

                elif tag in ("draw:text-box", "draw:frame"):
                    text = self.textToString(node)
                    buffer.append(text)

                elif tag in ("text:p", "text:h"):
                    text = self.paragraphToString(node)
                    if text:
                        buffer.append(text + "\n\n")

                elif tag in IGNORED_TAGS:
                    pass

                elif tag in INLINE_TAGS:
                    text = self.textToString(node)

                    if not text.strip():
                        continue  # don't apply styles to white space

                    styleName = node.getAttribute("text:style-name")
                    style = self.textStyles.get(styleName, TextProps())

                    if style.fixed:
                        buffer.append("`" + text + "`")
                        continue

                    if style:
                        if style.italic and style.bold:
                            mark = "'''''"
                        elif style.italic:
                            mark = "''"
                        elif style.bold:
                            mark = "'''"
                        else:
                            mark = ""
                    else:
                        mark = "/" + styleName + "/"

                    buffer.append("%s%s%s " % (mark, text, mark))


                else:
                    buffer.append(" {" + tag + "} ")

        return ''.join(buffer)

    def paragraphToString(self, paragraph, indent = 0):

        dummyParaProps = ParagraphProps()

        style_name = paragraph.getAttribute("text:style-name")
        paraProps = self.paragraphStyles.get(style_name, dummyParaProps)
        text = self.textToString(paragraph)

        #print style_name

        if paraProps and not paraProps.code:
            text = text.strip()

        if paraProps.title:
            self.hasTitle = 1
            return "= " + text + " =\n"

        outlinelevel = paragraph.getAttribute("text:outline-level")
        if outlinelevel:

            level = int(outlinelevel)
            if self.hasTitle: level += 1

            if level >= 1:
                return "\n" + "=" * level + " " + text + " " + "=" * level + "\n"

        elif paraProps.code:
            return "{{{\n" + text + "\n}}}\n"

        if paraProps.indented:
            return self.wrapParagraph(text, indent = indent, blockquote = True)

        else:
            return self.wrapParagraph(text, indent = indent)


    def wrapParagraph(self, text, indent = 0, blockquote=False):

        counter = 0
        buffer = []
        LIMIT = 50

        if blockquote:
            buffer.append("  ")

        return ''.join(buffer) + text
        for token in text.split():

            if counter > LIMIT - indent:
                buffer.append("\n" + " "*indent)
                if blockquote:
                    buffer.append("  ")
                counter = 0

            buffer.append(token + " ")
            counter += len(token)

        return ''.join(buffer)



if __name__ == "__main__":
    odt = OpenDocumentTextFile(sys.argv[1])
    unicode = odt.toString()
    out_utf8 = unicode.encode("utf-8")
    sys.stdout.write(out_utf8)

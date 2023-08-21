from typing import List, Optional, Union, Dict, Any
import json
import time
import datetime
import pytz
import uuid
import urllib.parse
import tiktoken

import mistune
from mistune.renderers.markdown import MarkdownRenderer
from mistune.core import BaseRenderer, BlockState
import pprint


# mistune==3.0.0rc5

def markdownToJson(text) -> List[Dict]:
    markdown = mistune.create_markdown(renderer='ast')
    markdownJson = markdown(text)
    return markdownJson


def timestampToIso(timestamp, timezone=pytz.timezone('America/Los_Angeles')):
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    local_dt = dt.astimezone(timezone)
    return local_dt.strftime('%Y-%m-%dT%H:%M:%S.%f%z')


# data = {
#   "message": {
#     "role": "assistant",
#     "content": "以下是用类的写法实现 hello world 的 Python 代码：\n\n```python\nclass HelloWorld:\n    def __init__(self):\n        self.message = \"Hello, World!\"\n\n    def __str__(self):\n        return self.message\n\nif __name__ == \"__main__\":\n    hw = HelloWorld()\n    print(hw)\n```\n\n执行以上代码输出结果为：\n\n```text\nHello, World!\n```"
#   },
#   "usage": {
#     "prompt_tokens": 21,
#     "completion_tokens": 84,
#     "total_tokens": 105
#   }

def generateUUID():
    return str(uuid.uuid1())


class BlockType:
    h1 = "h1"
    h2 = "h2"
    h3 = "h3"
    text = "rich_texts"
    list = "list"
    number_list = "number_list"
    checkbox = "checkbox"
    code = "code"
    quote = "quote"
    hr = "hr"
    webBookmark = "webBookmark"
    gallery = "gallery"
    embed = "embed"
    reference = "reference"
    vote = "vote"
    todos = "todos"
    file = "file"
    nest = "nest"
    table = "table"


class ElementType:
    inline_code = "inline_code"
    text = "text"
    bold = "bold"
    italic = "italic"
    link = "link"
    url = "url"
    escape = "escape"
    user = "user"
    image = "image"
    linkToPost = "linkToPost"
    math = "math"
    underLine = "underline"
    lineThrough = "line_through"
    backgroundColored = "backgroundColored"
    colored = "colored"


class Element:
    id: str
    text: str
    type: str
    elements: List
    isCurrent: bool
    value = None

    def __init__(self, data):
        self.id = data.get('id')
        self.text = data.get('text', "")
        self.type = data.get('type')
        self.elements = [Element.fromJson(e) for e in data.get('elements', [])]
        self.isCurrent = data.get('isCurrent', False)
        self.value = data.get('value', None)

    def getValue(self) -> str:
        if type(self.value) == str:
            return urllib.parse.quote(self.value, safe=':/')
        elif type(self.value) == dict and self.type == ElementType.image:
            return urllib.parse.quote(self.value.get("url", ""), safe=':/')
        return ""

    @classmethod
    def copyDefault(cls, type=ElementType.text, text=None, elements=None,
                    isCurrent=False, value=None):
        if not elements:
            elements = []
        return cls({
            "id": generateUUID(),
            "type": type,
            "text": text,
            "elements": [e.toJson() for e in elements],
            "isCurrent": isCurrent,
            "value": value
        })

    @classmethod
    def normalText(cls, text):
        return Element.copyDefault(
            text=text,
        )

    @classmethod
    def bold(cls, elements):
        return Element.copyDefault(
            type=ElementType.bold,
            elements=elements
        )

    @classmethod
    def italic(cls, elements):
        return Element.copyDefault(
            type=ElementType.italic,
            elements=elements
        )

    @classmethod
    def inlineCode(cls, text):
        return Element.copyDefault(
            type=ElementType.inline_code,
            text=None,
            elements=[Element.copyDefault(
                type=ElementType.text,
                text=text
            )]
        )

    @classmethod
    def link(cls, text, value):
        return Element.copyDefault(
            type=ElementType.link,
            text="",
            value=value,
            elements=[
                Element.copyDefault(
                    text=text
                )
            ]
        )

    @classmethod
    def image(cls, text, value):
        return Element.copyDefault(
            type=ElementType.image,
            text="",
            value={
                "id": generateUUID(),
                "name": "",
                "uploadFailed": False,
                "uploaded": True,
                "uploading": False,
                "url": value
            }
        )

    @classmethod
    def user(cls, name, memberId):
        return Element.copyDefault(
            type=ElementType.user,
            text=name,
            value=memberId
        )

    @classmethod
    def fromJson(cls, data: dict):
        return cls(data)

    def toJson(self):
        _elements = []
        if len(self.elements) > 0:
            _elements = [e.toJson() for e in self.elements]
        return {
            "id": self.id,
            "type": self.type,
            "text": self.text,
            "elements": _elements,
            "isCurrent": self.isCurrent,
            "value": self.value
        }

    def render(self):
        out = [self.toJson()]
        if self.type in [
            ElementType.bold,
            ElementType.italic,
            ElementType.inline_code,
            ElementType.link
        ]:
            out = [
                      Element.normalText(text="").toJson(),
                  ] + out + [
                      Element.normalText(text="").toJson(),
                  ]
        return out

    def toMarkdown(self):
        if self.type == ElementType.text:
            return self.text
        elif self.type == ElementType.url:
            return self.text
        elif self.type == ElementType.inline_code:
            return "`" + "".join([e.toMarkdown() for e in self.elements]) + "`"
        elif self.type == ElementType.bold:
            return "**" + "".join(
                [e.toMarkdown() for e in self.elements]) + "**"
        elif self.type == ElementType.italic:
            return "*" + "".join([e.toMarkdown() for e in self.elements]) + "*"
        elif self.type == ElementType.link:
            return "[" + "".join([e.toMarkdown() for e in
                                  self.elements]) + "](" + self.getValue() + ")"
        elif self.type == ElementType.escape:
            return self.text
        elif self.type == ElementType.user:
            return "@" + self.text
        elif self.type == ElementType.image:
            return "![](" + self.getValue() + ")"
        elif self.type == ElementType.linkToPost:
            return "[A link to other post]"
        elif self.type == ElementType.math:
            return "$" + self.text + "$"
        elif self.type == ElementType.underLine:
            return "".join([e.toMarkdown() for e in self.elements])
        elif self.type == ElementType.lineThrough:
            return "~" + "".join([e.toMarkdown() for e in self.elements]) + "~"
        elif self.type == ElementType.backgroundColored:
            return "".join([e.toMarkdown() for e in self.elements])
        elif self.type == ElementType.colored:
            return "".join([e.toMarkdown() for e in self.elements])
        else:
            return self.text


class Block:
    id: str
    type: str
    blocks: List
    indent: int
    seqNum: int
    display: str
    isFirst: bool
    version: int
    elements: List
    isCurrent: bool
    constraint: str
    lastEditedBy: Optional[str]
    lastEditedTime: Optional[str]
    updatedByRemote: Optional[bool]
    computedValue = None
    userDefinedValue = None
    isDeleted: Optional[bool] = None

    def __init__(self, data):
        self.id = data.get('id')
        self.type = data.get('type')
        self.blocks = [Block.fromJson(b) for b in data.get('blocks', [])]
        self.indent = data.get('indent', 0)
        self.seqNum = data.get('seqNum', 0)
        self.display = data.get('display', "block")
        self.isFirst = data.get('isFirst', False)
        self.version = data.get('version', 0)
        self.elements = [Element.fromJson(e) for e in data.get('elements', [])]
        self.isCurrent = data.get('isCurrent', False)
        self.constraint = data.get('constraint', "free")
        self.lastEditedBy = data.get('lastEditedBy', None)
        self.lastEditedTime = data.get('lastEditedTime', None)
        self.updatedByRemote = data.get('updatedByRemote', False)
        self.computedValue = data.get('computedValue', None)
        self.userDefinedValue = data.get('userDefinedValue', None)
        self.isDeleted = data.get('isDeleted', None)


    @classmethod
    def fromJson(cls, data: dict):
        return cls(data)

    def toJson(self):
        _blocks = []
        if len(self.blocks) > 0:
            _blocks = [b.toJson() for b in self.blocks]
        _elements = []
        if len(self.elements) > 0:
            _elements = [e.toJson() for e in self.elements]
        return {
            "id": self.id,
            "type": self.type,
            "isFirst": self.isFirst,
            "indent": self.indent,
            "blocks": _blocks,
            "display": self.display,
            "elements": _elements,
            "isCurrent": self.isCurrent,
            "constraint": self.constraint,
            "lastEditedBy": self.lastEditedBy,
            "lastEditedTime": self.lastEditedTime,
            "updatedByRemote": self.updatedByRemote,
            "computedValue": self.computedValue,
            "userDefinedValue": self.userDefinedValue,
        }

    @classmethod
    def copyDefault(cls, type=BlockType.text, indent=0, display="block",
                    isCurrent=False, constraint="free",
                    blocks=None, elements=None, computedValue=None,
                    userDefinedValue=None):
        if not blocks:
            blocks = []
        _elements = elements if elements is not None else [
            Element.normalText(text="")
        ]
        return cls({
            "id": generateUUID(),
            "type": type,
            "isFirst": False,
            "indent": indent,
            "blocks": [b.toJson() for b in blocks],
            "display": display,
            "elements": [e.toJson() for e in _elements],
            "isCurrent": False,
            "constraint": "free",
            "lastEditedBy": None,
            "lastEditedTime": None,
            "updatedByRemote": False,
            "computedValue": computedValue,
            "userDefinedValue": userDefinedValue
        })

    @classmethod
    def raw(cls, text):
        return Block.copyDefault(
            type=BlockType.text,
            elements=[
                Element.normalText(text=text),
            ]
        )

    @classmethod
    def h1(cls, elements: List[Element]):
        return Block.copyDefault(
            type=BlockType.h1,
            elements=elements
        )

    @classmethod
    def h2(cls, elements: List[Element]):
        return Block.copyDefault(
            type=BlockType.h2,
            elements=elements
        )

    @classmethod
    def h3(cls, elements: List[Element]):
        return Block.copyDefault(
            type=BlockType.h3,
            elements=elements
        )

    @classmethod
    def rich_texts(cls, elements: List[Element]):
        return Block.copyDefault(
            type=BlockType.text,
            elements=elements
        )

    @classmethod
    def bulletList(cls, elements: List[Element]):
        return Block.copyDefault(
            type=BlockType.list,
            elements=elements
        )

    @classmethod
    def numberList(cls, elements: List[Element]):
        return Block.copyDefault(
            type=BlockType.number_list,
            elements=elements
        )
    
    @classmethod
    def gallery(cls, elements: List[Element]):
        return Block.copyDefault(
            type=BlockType.gallery,
            elements=elements
        )

    def render(self):
        return [self.toJson()]

    def getNumberPrefix(self) -> str:
        if self.userDefinedValue != None and type(self.userDefinedValue) is str:
            return self.userDefinedValue
        elif self.computedValue != None and type(self.computedValue) is str:
            return self.computedValue
        else:
            return "1."

    def getCheckboxValue(self) -> str:
        if self.userDefinedValue != None and type(
                self.userDefinedValue) is dict:
            return self.userDefinedValue.get("status", "unchecked")
        return "unchecked"

    def getCodeLang(self) -> str:
        if self.userDefinedValue != None and type(
                self.userDefinedValue) is dict:
            return self.userDefinedValue.get("language", "plain")
        return "plain"

    def getWebBookmarkUrl(self) -> str:
        if self.userDefinedValue != None and type(
                self.userDefinedValue) is dict:
            return urllib.parse.quote(
                self.userDefinedValue.get("url", "https://#"), safe=':/')
        if self.userDefinedValue != None and type(self.userDefinedValue) is str \
            and self.userDefinedValue.startswith("https://"):
            return urllib.parse.quote(
                self.userDefinedValue, safe=':/')

        return "https://#"

    def getFileUrl(self) -> str:
        if self.userDefinedValue != None and type(
                self.userDefinedValue) is dict:
            return urllib.parse.quote(
                self.userDefinedValue.get("url", "https://#"), safe=':/')
        return "https://#"

    def getEmbedValue(self) -> tuple:
        defaultEmbed = '<iframe src="https://www.trickle.so" class="w-full" allow="autoplay" allowfullscreen></iframe>'
        if self.userDefinedValue != None and type(
                self.userDefinedValue) is dict:
            return (self.userDefinedValue.get("height", 300),
                    self.userDefinedValue.get("src", defaultEmbed))
        return (300, defaultEmbed)

    def getPollCounts(self, bid):
        if self.userDefinedValue != None and type(
                self.userDefinedValue) is dict:
            return len(self.userDefinedValue.get("vote-" + bid, []))
        return 0

    def voteToMarkdown(self):
        if len(self.blocks) != 3:
            return ""
        h1 = self.blocks[0]
        desc = self.blocks[1]
        options = self.blocks[2]
        out = "\n"
        out = "## Poll Title: " + "".join([e.toMarkdown() for e in h1.elements])
        out = out + "\n" + "Poll Description: " + desc.toMarkdown()
        out = out + "\n" + "| option | poll counts |"
        out = out + "\n" + "| ------------ | ------------ |"
        for op in options.blocks:
            out = out + "\n" + "| " + op.toMarkdown() + " | " + str(
                self.getPollCounts(op.id)) + " |"
        out = out + "\n"
        return out

    def tableToMarkdown(self):
        # table内容藏在了 blocks的userDefinedValue的content中。
        tableContent = self.userDefinedValue.get('content')
        withHeadings = self.userDefinedValue.get('withHeadings')
        out = "\n"
        # 添加表头， tableContent[0]就是表头:
        headings = tableContent.pop(0)
        for perhead in headings:
            out = out + " | " + f'{perhead}'
        out = out + " |" + "\n"
        for _ in headings:
            out = out + " | " + "------------ "
        out = out + " |" + "\n"

        for perRow in tableContent:
            for perColum in perRow:
                out = out + " | " + f'{perColum}'
            out = out + " |" + "\n"

        return out

    def toDosToMarkdown(self):
        if len(self.blocks) != 3:
            return ""
        h1 = self.blocks[0]
        desc = self.blocks[1]
        options = self.blocks[2]
        out = "\n"
        out = "## Tasks Title: " + "".join(
            [e.toMarkdown() for e in h1.elements])
        out = out + "\n" + "Tasks Description: " + desc.toMarkdown()
        for op in options.blocks:
            out = out + "\n" + op.toMarkdown()
        out = out + "\n"
        return out

    def toMarkdown(self):
        if self.type == BlockType.h1:
            return "# " + "".join([e.toMarkdown() for e in self.elements])
        elif self.type == BlockType.h2:
            return "## " + "".join([e.toMarkdown() for e in self.elements])
        elif self.type == BlockType.h3:
            return "### " + "".join([e.toMarkdown() for e in self.elements])
        elif self.type == BlockType.text:
            return "".join([e.toMarkdown() for e in self.elements])
        elif self.type == BlockType.list:
            return "- " + "".join([e.toMarkdown() for e in self.elements])
        elif self.type == BlockType.number_list:
            return self.getNumberPrefix() + " " + "".join(
                [e.toMarkdown() for e in self.elements])
        elif self.type == BlockType.checkbox:
            return "- [" + (
                " " if self.getCheckboxValue() == "unchecked" else "x") + "] " + "".join(
                [e.toMarkdown() for e in self.elements])
        elif self.type == BlockType.code:
            return "```" + self.getCodeLang() + "\n" + "".join(
                [e.toMarkdown() for e in self.elements]) + "\n```"
        elif self.type == BlockType.quote:
            return "\n".join(["> " + b.toMarkdown() for b in self.blocks])
        elif self.type == BlockType.webBookmark:
            return "[WebBookmark](" + self.getWebBookmarkUrl() + ")"
        elif self.type == BlockType.embed:
            embedValues = self.getEmbedValue()
            return "```html\n<html><body style='height: " + str(
                embedValues[0]) + "px'>" + embedValues[
                1] + "</body></html>" + "\n```"
        elif self.type == BlockType.gallery:
            return "".join([e.toMarkdown() for e in self.elements])
        elif self.type == BlockType.reference:
            return "".join([e.toMarkdown() for e in self.elements])
        elif self.type == BlockType.hr:
            return "---"
        elif self.type == BlockType.vote:
            return self.voteToMarkdown()
        elif self.type == BlockType.todos:
            return self.toDosToMarkdown()
        elif self.type == BlockType.file:
            return "[Attachment](" + self.getFileUrl() + ")"

        elif self.type == BlockType.table:
            return self.tableToMarkdown()

        return ""


class TrickleBlockRenderer(MarkdownRenderer):
    """A renderer to convert markdown to Trickle Block."""
    NAME = 'TrickleBlock'

    def __call__(self, tokens, state: BlockState) -> List[Block]:
        out = []
        blocks = self.render_blocks(tokens, state)
        for b in blocks:
            out = out + b.render()
        return out

    elementType = ['emphasis', 'strong', 'link', 'image', 'codespan',
                   'inline_html', 'linebreak']

    def getRawText(self, token: Dict[str, Any]) -> str:

        out = ''
        if len(token.get("children", [])) > 0:
            for perSubToken in token.get("children", []):
                out = out + self.getRawText(perSubToken)
        if token.get("raw") is not None:
            return token["raw"]
        if token.get("type") == 'softbreak' and token.get("raw") is None:
            return '\n'
        if token.get("type") in self.elementType and token.get("raw") is None:
            return ''
        # if token["type"] == "block_text":
        #     out = out + "\n"
        return out

    def render_children(self, token, state: BlockState):
        children = token['children']
        return self.render_tokens(children, state)

    def _get_element_method(self, name):
        if name == "text":
            return self.text
        elif name == "emphasis":
            return self.emphasis
        elif name == "strong":
            return self.strong
        elif name == "link":
            return self.link
        elif name == "image":
            return self.image
        elif name == "codespan":
            return self.codespan
        elif name == "inline_html":
            return self.inline_html
        elif name == "softbreak":
            return self.softbreak
        elif name == "linebreak":
            return self.linebreak
        else:
            return self.defalut_element_render

    def defalut_element_render(self, token: Dict[str, Any],
                               state: BlockState) -> List[Element]:
        text = self.getRawText(token)
        print(f'defalut_element_render: {text=}')
        return [Element.normalText(
            text=text
        )]

    def _combine_text_and_lineBreak_elements(self, elements):
        i = 0
        newElements = []
        newElementStr = ''
        unionType = ['text', 'linebreak', 'softbreak']
        while i < len(elements):
            # 是text或者linebreak类型的话就累加
            if elements[i].type in unionType:
                newElementStr = newElementStr + elements[i].text

            # 一旦发现不是text或者linebreak类型， 就应该保存起来
            else:

                if newElementStr:
                    rawStr = newElementStr
                    newElements.append(Element.normalText(text=rawStr))
                    newElementStr = ''

                newElements.append(elements[i])

            if i == len(elements) - 1 and newElementStr:
                rawStr = newElementStr
                newElements.append(Element.normalText(text=rawStr))
            i = i + 1

        return newElements

    def _combine_text_and_lineBreak_tokens(self, tokens: List[Dict]):

        newTokens = []
        newTokenStr = ''
        unionType = ['text', 'linebreak', 'softbreak']
        for t in tokens:
            if t['type'] == 'linebreak':
                t['raw'] = '\n'

            if t['type'] == 'softbreak':
                t['raw'] = '\n'
        i = 0
        while i < len(tokens):

            # 是text或者linebreak类型的话就累加
            if tokens[i]['type'] in unionType:
                newTokenStr = newTokenStr + tokens[i]['raw']

            # 一旦发现不是text或者linebreak类型， 就应该保存起来
            else:

                if newTokenStr:
                    rawStr = newTokenStr
                    newTokens.append({'raw': rawStr, 'type': 'text'})
                    newTokenStr = ''

                newTokens.append(tokens[i])

            if i == len(tokens) - 1 and newTokenStr:
                rawStr = newTokenStr
                newTokens.append({'raw': rawStr, 'type': 'text'})
            i = i + 1

        return newTokens

    def render_elements(self, tokens: List[Dict], state: BlockState) -> List[
        Element]:
        elements = []
        newTokens = self._combine_text_and_lineBreak_tokens(tokens)
        for t in newTokens:
            func = self._get_element_method(t["type"])
            elements = elements + func(t, state)
        newElements = self._combine_text_and_lineBreak_elements(elements)
        return newElements

    def _get_block_method(self, name):
        if name == "heading":
            return self.heading
        elif name == "paragraph":
            return self.paragraph
        elif name == "block_code":
            return self.block_code
        elif name == "list":
            return self.list
        elif name == "block_quote":
            return self.block_quote
        elif name == "blank_line":
            return self.blank_line
        else:
            return self.defalut_block_render

    def render_blocks(self, tokens: List[Dict], state: BlockState) -> List[
        Block]:
        blocks = []
        for b in tokens:
            print(f'render_blocks:')
            pprint.pprint(b)
            func = self._get_block_method(b["type"])
            blocks = blocks + func(b, state)
        return blocks

    def defalut_block_render(self, token: Dict[str, Any], state: BlockState) -> \
    List[Block]:
        text = self.getRawText(token)
        return [Block.raw(text=text)]

    def text(self, token: Dict[str, Any], state: BlockState) -> List[Element]:
        # {'raw': 'Headline 1', 'type': 'text'}
        return [Element.normalText(
            text=token.get("raw", "")
        )]

    def emphasis(self, token: Dict[str, Any], state: BlockState) -> List[
        Element]:
        # {'children': [{'raw': 'Python', 'type': 'text'}],'type': 'emphasis'}
        return [Element.italic(
            elements=self.render_elements(token.get("children", []), state)
        )]

    def strong(self, token: Dict[str, Any], state: BlockState) -> List[Element]:
        # {'children': [{'raw': 'hello world', 'type': 'text'}],'type': 'strong'}
        return [Element.bold(
            elements=self.render_elements(token.get("children", []), state)
        )]

    def link(self, token: Dict[str, Any], state: BlockState) -> List[Element]:
        url = token.get('attrs',{}).get('url','https://#')
        rawText = self.getRawText(token=token)
        if rawText == "":
            rawText = url
        return [Element.link(
            text=rawText,
            value=url
        )]

    def image(self, token: Dict[str, Any], state: BlockState) -> List[Element]:
        return [Element.image(
            text="",
            value=token.get('attrs',{}).get('url','https://#')
        )]

    def codespan(self, token: Dict[str, Any], state: BlockState) -> List[
        Element]:
        # {'raw': '类', 'type': 'codespan'}
        return [Element.inlineCode(
            text=token.get("raw", "")
        )]

    def inline_html(self, token: Dict[str, Any], state: BlockState) -> List[
        Element]:
        return [Element.inlineCode(
            text=token.get("raw", "")
        )]

    def block_text(self, token: Dict[str, Any], state: BlockState) -> List[
        Element]:
        return self.render_elements(token.get("children", []),
                                    state)  # + [Element.normalText(text="\n")]

    def softbreak(self, token: Dict[str, Any], state: BlockState) -> List[
        Element]:
        return [Element.normalText(
            text="\n"
        )]

    def linebreak(self, token: Dict[str, Any], state: BlockState) -> List[
        Element]:
        return [
            Element.normalText(
                text="  \n"
            )
        ]

    def blank_line(self, token: Dict[str, Any], state: BlockState) -> List[
        Block]:
        # {'type': 'blank_line'}
        return [Block.raw(text="")]
        # return []

    def paragraph(self, token: Dict[str, Any], state: BlockState) -> List[
        Block]:
        out = []
        otherTokens = []
        childrenTokens = token.get("children", [])
        for perC in childrenTokens:
            if perC.get("type","") == ElementType.image:
                if len(otherTokens) > 0:
                    out.append(Block.copyDefault(
                        type=BlockType.text,
                        elements=self.render_elements(otherTokens, state)
                    ))
                    otherTokens = []
                out.append(Block.gallery(
                    elements=self.render_elements([perC], state)
                ))
            else:
                otherTokens.append(perC)
        if len(otherTokens) > 0:
            out.append(Block.copyDefault(
                type=BlockType.text,
                elements=self.render_elements(otherTokens, state)
            ))
        return out

    def heading(self, token: Dict[str, Any], state: BlockState) -> List[Block]:
        # {'attrs': {'level': 1},
        # 'children': [{'raw': 'Headline 1', 'type': 'text'}],
        # 'style': 'axt',
        # 'type': 'heading'}
        hLevel = token.get("attrs", {}).get("level", 3)
        if hLevel == 1:
            bType = BlockType.h1
        elif hLevel == 2:
            bType = BlockType.h2
        else:
            bType = BlockType.h3
        return [Block.copyDefault(
            type=bType,
            elements=self.render_elements(token.get("children", []), state)
        )]

    def thematic_break(self, token: Dict[str, Any], state: BlockState) -> List[
        Block]:
        return [Block.raw(text=token.get("raw", ""))]

    def block_code(self, token: Dict[str, Any], state: BlockState) -> List[
        Block]:
        # {'attrs': {'info': 'python'},
        # 'marker': '```',
        # 'raw': 'class HelloWorld:\n'
        #         '    def __init__(self):\n'
        #         '        self.message = "Hello, World!"\n'
        #         '\n'
        #         '    def __str__(self):\n'
        #         '        return self.message\n'
        #         '\n'
        #         'if __name__ == "__main__":\n'
        #         '    hw = HelloWorld()\n'
        #         '    print(hw)\n',
        # 'style': 'fenced',
        # 'type': 'block_code'}
        return [Block.copyDefault(
            type=BlockType.code,
            elements=[
                Element.normalText(
                    text=token.get("raw", "")
                )
            ],
            userDefinedValue={
                "language": token.get("attrs", {}).get("info", "plain")
            }
        )]

    def block_quote(self, token: Dict[str, Any], state: BlockState) -> List[
        Block]:
        # {'children': [{'children': [{'raw': 'Quote Message:', 'type': 'text'}],
        #         'type': 'paragraph'},
        #        {'attrs': {'depth': 1, 'ordered': False},
        #         'bullet': '-',
        #         'children': [{'children': [{'children': [{'raw': 'point 1',
        #                                                   'type': 'text'}],
        #                                     'type': 'block_text'}],
        #                       'type': 'list_item'},
        #                      {'children': [{'children': [{'raw': 'point 2',
        #                                                   'type': 'text'}],
        #                                     'type': 'block_text'}],
        #                       'type': 'list_item'}],
        #         'tight': True,
        #         'type': 'list'}],
        # 'type': 'block_quote'}
        return [Block.copyDefault(
            type=BlockType.quote,
            blocks=self.render_blocks(token.get("children", []), state)
        )]

    def block_html(self, token: Dict[str, Any], state: BlockState) -> List[
        Block]:
        return [Block.copyDefault(
            type=BlockType.code,
            elements=[
                Element.normalText(
                    text=token.get("raw", "")
                )
            ],
            userDefinedValue={
                "language": "html"
            }
        )]

    def block_error(self, token: Dict[str, Any], state: BlockState) -> List[
        Block]:
        print(token.get("raw", ""))
        return []

    def list(self, token: Dict[str, Any], state: BlockState) -> List[Block]:
        attrs = token['attrs']
        if attrs['ordered']:
            return self.render_numberpoint_list(token, state)
        else:
            return self.render_bulletpoint_list(token, state)

    def render_bulletpoint_list(self, token: Dict[str, Any],
                                state: BlockState) -> List[Block]:
        outs = []
        for b in token.get("children", []):
            outs.append(
                Block.copyDefault(
                    type=BlockType.list,
                    elements=self.render_elements(b.get("children", []), state)
                )
            )
        return outs

    def render_numberpoint_list(self, token: Dict[str, Any],
                                state: BlockState) -> List[Block]:
        outs = []
        i = 0
        for b in token.get("children", []):
            i = i + 1
            perBlock = Block.copyDefault(
                type=BlockType.number_list,
                elements=self.render_elements(b.get("children", []), state),
                computedValue=str(i) + ".",
                userDefinedValue=str(i) + "."
            )
            outs.append(perBlock)
        return outs


# 创建一个comment blocks
# askedMemberInfo = { id: <memberId>, name: "samdy"}
def createAssistantCommentBlocks(messageFromAI: str) -> list[Dict]:
    # _blocks: list[Block] = []
    # # append ai message block
    # _blocks.append(Block.copyDefault(
    #     elements=[
    #         Element.normalText(
    #             text=messageFromAI
    #         )
    #     ]
    # ))
    # # output
    # out = []
    # for b in _blocks:
    #     out = out + b.render()
    # return out
    markdown = mistune.create_markdown(renderer=TrickleBlockRenderer(),
                                       hard_wrap=True)
    out = markdown(messageFromAI)
    print(f'createAssistantCommentBlocks: {out=}')
    return out


# 计算一个文本的tokens
def getTextTokens(text):
    tic = time.time()
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    out = len(encoding.encode(text))
    toc = time.time()
    print("=====> getTextTokens duration: " + str(toc - tic))
    return out


# 输入字符串 和 maxTokens，截取出符合 maxTokens 的字符串
def truncateText(text, maxTokens):
    """Truncate a string to have `max_tokens` according to the given encoding."""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return encoding.decode(encoding.encode(text)[:maxTokens])


def blocksToMarkdown(blocks):
    out: List[str] = []
    for perBlk in blocks:
        blk = Block(perBlk)
        if blk.isDeleted:
            continue
        out.append(blk.toMarkdown())
    return "\n".join(out)


def generateTrickleContentPrompt(title: str, blocks: list, maxTokens=1500):
    out = ""
    if title and title != '':
        out = out + title + "\n"

    out = out + blocksToMarkdown(blocks)
    if maxTokens is None:
        convertToStr = out
    else:
        convertToStr = truncateText(out, maxTokens)
    result = convertToStr
    return result


def generateTrickleFieldDataPrompt(data: dict, maxTokens=None):
    """
    data =
    {
        fieldName1 : value1,
        fieldName2: value2,
        fieldName3: value3
    }
    """

    # 想要什么样的格式？
    convertToStrList = []
    for k, v in data.items():
        s = f"{k}:{v}"
        convertToStrList.append(s)
    convertToStr = "\n".join(convertToStrList)
    result = convertToStr
    return result


def generateTrickleStatusCommentPrompt(statusComments: list, maxTokens=None):
    '''
        stautsComents must be sorted before handling!!!

        statusComments:
        [{'john': comment1str }, {'mary': comment2str}]

    '''
    # 过滤掉所有是update this trickle的status comment
    # 取最近50条
    # ["commenName": "blocks的markDown"]

    newCommentList = []
    for comment in statusComments:
        if 'updated this post' in comment:
            continue
        for k, v in comment.items():
            commentStr = f"{k}: {v}"
            newCommentList.append(commentStr)
        if len(newCommentList) == 50:
            break

    convertToStr = "\n".join(newCommentList)
    result = convertToStr
    return result


def generateTrickleNormalCommentPrompt(comments: list, maxTokens=1000):
    # 提取最近 N 条的comments
    '''
        comments must be sorted before handling!!!

        comments:
        [{'commentId':  123456
          'commentBlocks': commentblocks,
          'commentAuthorName': 'John'   }, ... , ...]

        commentblocks: list[dict] in block format
    '''
    commentPromptWithIds = {}
    newCommentList = []
    for comment in comments:
        if comment['commentBlocks'] is None:
            print("ERROR: comment blocks is none")
            print(comment)
            continue
        block = blocksToMarkdown(comment['commentBlocks'])
        commentStr = f"{comment['commentAuthorName']}: {block}"
        commentPromptWithIds[comment["commentId"]] = commentStr
        newCommentList.append(commentStr)

    commentOriginPrompt = "\n".join(newCommentList)
    if maxTokens is None:
        commentPrompt = commentOriginPrompt
    else:
        usedTokens = 0
        truncateCommentList = []
        for perComment in newCommentList[::-1]:
            commentTokens = getTextTokens(perComment)
            usedTokens += commentTokens
            if maxTokens - usedTokens < 0:
                break
            truncateCommentList.append(perComment)
        commentPrompt = "\n".join(truncateCommentList[::-1])

    return commentPromptWithIds, commentPrompt


def generateAssistantPrompts(userInputMessage, assistantSetting):
    prompts = []
    # 1. system prompts
    systemPrompt = assistantSetting.get("system", "")
    print(f'{assistantSetting=}')
    print(f'{systemPrompt=}')
    if systemPrompt is not None and systemPrompt != "":
        prompts.append({
            "role": "system",
            "content": systemPrompt
        })
    # 2. userInput prompts
    prompts.append({
        "role": "user",
        "content": assistantSetting.get("prefix",
                                        "") + userInputMessage + assistantSetting.get(
            "suffix", "")
    })
    return prompts


if __name__ == "__main__":
    # # block data path
    # blockDataFile = "data/trickle_blocks_02.json"

    # blocksData = json.load(open(blockDataFile))

    # blocks: List[Block] = []
    # for perBlk in blocksData:
    #     blocks.append(Block(perBlk))

    # for b in blocks:
    #     print(b.toMarkdown())

    # text = "# Headline 1\n\n~API Name~\n- point1 (https://www.trickle.so)\n- point2\n- point3\n\n`Tasks`\n- [ ] Task01\n- [ ] Task 02\n- [x] Task 03\n\n`Number points`\n1. number01\n2. number02\n3. number 03\n\n以下是用`类`的写法实现 **hello world** 的 *Python* 代码：\n\n```python\nclass HelloWorld:\n    def __init__(self):\n        self.message = \"Hello, World!\"\n\n    def __str__(self):\n        return self.message\n\nif __name__ == \"__main__\":\n    hw = HelloWorld()\n    print(hw)\n```\n\n执行以上代码输出结果为：\n\n```text\nHello, World!\n```\n\n> Quote Message: \n> - point 1\n> - point 2"
    # #text = "# Headline 1\n\n`API Name`\n- point1\n- point2\n- point3\n\n`Tasks`\n- [ ] Task01\n- [ ] Task 02\n- [x] Task 03\n\n`Number points`\n1. number01\n2. number02\n3. number 03\n\n以下是用`类`的写法实现 **hello world** 的 *Python* 代码：\n\n```python\nclass HelloWorld:\n    def __init__(self):\n        self.message = \"Hello, World!\"\n\n    def __str__(self):\n        "
    # text = "class Hello:\n def say_hello(self):\n print(\"Hello World\")\n\nhello = Hello()\nhello.say_hello()"
    # markdown = mistune.create_markdown(renderer=TrickleBlockRenderer(), hard_wrap=True)
    # markdownJson = markdown(text)
    # pprint.pprint(markdownJson)
    # json.dump(markdownJson, open("blocks.json",'w'))
    #
    # aim2 = '1) This could be a game changer for website design! Can it be integrated with popular website builders like Wix or Squarespace?\n2) Finally, a tool that can help streamline web design. Kudos to the Trickle AI team!\n3) I love the idea of having AI assist with web design. Excited to see what Trickle AI can do!'
    # aim3 = 'Sure, here are some Unsplash links that you can use to find high-resolution images for your desktop background:\n\n1. https://unsplash.com/\n2. https://unsplash.com/wallpapers/desktop\n3. https://unsplash.com/collections/desktop-wallpapers\n4. https://unsplash.com/search/photos/desktop-background\n5. https://unsplash.com/s/photos/high-resolution-desktop-wallpaper\n\nI hope this helps! Let me know if you need further assistance.'
    # aim4 = '| Product Name | ID | Qty | Price |\n|--------------|------|-----|-------|\n| Apple | 1001 | 10 | $1.00 |\n| Banana | 1002 | 5 | $0.50 |\n| Orange | 1003 | 8 | $0.75 |\n| Grapes | 1004 | 3 | $2.50 |'
    #
    # aim5 = '好的，让我为您展示如何使用Vue 3来创建一个简单的登陆注册页面吧。首先，让我们从基本结构开始：\n```html\n<template>\n  <div>\n    <h1>Login/Register</h1>\n    <form>\n      <div>\n        <label for="username">Username:</label>\n        <input type="text" id="username" v-model="username">\n      </div>\n      <div>\n        <label for="password">Password:</label>\n        <input type="password" id="password" v-model="password">\n      </div>\n      <button type="submit" @click.prevent="submitForm">Submit</button>\n      <button type="button" @click="toggleFormMode">{{ mode === \'login\' ? \'Register\' : \'Login\' }}</button>\n    </form>\n  </div>\n</template>\n\n<script>\n  export default {\n    data() {\n      return {\n        mode: \'login\', // 初始状态为登陆\n        username: \'\',\n        password: \'\'\n      }\n    },\n    methods: {\n      toggleFormMode() {\n        // 切换登录/注册模式\n        this.mode = this.mode === \'login\' ? \'register\' : \'login\';\n      },\n      submitForm() {\n        // 处理表单提交逻辑\n        console.log(`Submitted ${this.mode} form with username=${this.username} and password=${this.password}`);\n      }\n    }\n  }\n</script>\n\n```\n在这个例子中，我们有一个初始状态为登陆的表单，但用户可以通过点击切换到注册模式。另外，我们收集了用户名和密码信息，并在表单提交时记录这两个值。\n请注意，此代码仅包含在单个文件中的组件代码。因此，可以将其直接导入到你的应用程序中以使用该组件。\n希望这个简单的例子能为您提供一些帮助！如果您有任何其他问题，请随时问我。'
    # markdown = mistune.create_markdown(renderer=TrickleBlockRenderer(),
    #                                    hard_wrap=True)
    # markdownJson = markdown(aim5)
    # pprint.pprint(markdownJson)

    # pprint.pprint()


    tableBlocks = [{
    "id": "QyWIn2dA3w",
    "type": "table",
    "blocks": [],
    "elements": [],
    "userDefinedValue": {
        "withHeadings": True,
        "content": [
            [
                "1",
                "2"
            ]
        ]
    },
    "indent": 0
}]

    result = blocksToMarkdown(tableBlocks)
    print(result)

    # out = createAssistantCommentBlocks(
    #     messageFromAI=aim2
    # )
    # pprint.pprint(out)
    # json.dump(out, open("blocks.json",'w'))

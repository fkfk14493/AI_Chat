import streamlit as st
from google import genai
from google.genai import types
import db_handler as db

# 데이터베이스 초기화 및 기존 대화 기록 불러오기
db.init_db()
if "messages" not in st.session_state:
    st.session_state.messages = db.load_chat()

# [수정] 브라우저 기본 레이아웃에서 불필요한 여백을 줄이고 깔끔하게 세팅
st.set_page_config(page_title="Chatting", layout="centered")

# [수정] 스트림릿 특유의 상단 여백(헤더 공백)을 강제로 제거하는 CSS 주입
st.markdown("""
    <style>
        /* 상단 공백 제거 */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
        /* 우측 상단 스트림릿 메뉴 숨기기 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# API 설정
API_KEY = "AQ.Ab8RN6JeuxZlXp7eeMxSvorsFJfyMt7Nh1vVXahcLjr8iixvFg"

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=API_KEY)

# 소고의 캐릭터 설정
char_persona = (
    "너랑 나는 역할극을 하고 있어. 아래의 규칙을 철저히 지켜서 자연스러운 어조로 답해줘. 대본을 쓰듯 소설형 전개를 해주고, 적극적으로 스토리를 전개해줘. 행동 묘사나 주위 배경 서술은 '*서술*'로 표시. \n\n"
    "너는 만화 '은혼'의 등장인물 진선조 1번대 대장 '오키타 소고'야. 외형은 귀여운 미소년 계. 잘생긴 얼굴, 적색 눈동자와 밤색 머리칼을 가짐. 나이는 18살. 일 중에는 제복을, 아닐 때는 유카타를 입음. 성격은 나른하지만 도S 사디스트의 성격을 가지고 있음. 히지카타에 대해 애증을 품고 있어 틈만 나면 죽이거나 괴롭히려 들음."
    "과거: 무사들의 고향인 무주(武州) 출신. 일찍 부모를 여의고 유일한 혈육이자 가장 사랑하는 친누나 '오키타 미츠바'의 손에 과보호에 가깝게 자람.  어린 시절 천재적인 검술 재능을 보이며 곤도 이사오의 도장에 들어감. 소고에게 곤도는 단순한 스승을 넘어 부모이자 세상의 전부와 다름없는 존재. 이후 도장에 들어온 '히지카타 토시로'에게 곤도의 관심과 누나 미츠바의 연정마저 빼앗겼다고 생각하며 질투심을 느낌. 이후 곤도를 따라 에도로 상경하여 막부의 특수 경찰 기구인 '진선조 1번대 대장'이 됨."
    "주요 인물 관계성:\n"
    "곤도 이사오 (국장): 순종하고 따르는 정신적 지주이자 절대적인 존재. 누나 미츠바가 세상을 떠난 후, 곤도는 소고에게 남은 마지막 가족이자 지켜야 할 빛이다. 곤도를 지키기 위해서라면 언제든 자신의 목숨을 던질 준비가 되어 있다. '소고', '콘도 씨'로 서로 부르고 있다. 참고로 곤도는 히지카타를 '토시'라고 부른다."
    "히지카타 토시로 (부장):  표면적으로는 매일 바주카를 쏘며 목숨을 노리는 철천지원수이자 증오의 대상. 곤도의 총애를 독차지하고 사랑하는 누나를 울린 장본인이라 여겨 극도로 미워한다. 하지만 내면 깊은 곳에서는 히지카타의 실력과 신념을 누구보다 인정하고 신뢰하고 있다. 앙숙처럼 으르렁거리면서도 진선조의 기틀을 유지하기 위해 기꺼이 등을 맡기는 기묘하고 복잡한 애증의 라이벌 관계다. '소고', '히지카타 씨'로 서로 부르고 있다."
    """사카타 긴토키 (해결사): 소고가 진선조 인물들을 제외하고 유일하게 '형씨'라고 부르며 따르고 의지하는 존재.  평소에는 히지카타를 골탕 먹이기 위해 의기투합하는 '땡땡이 콤비'이자 악우에 가깝지만, 긴토키의 압도적인 무력과 어른스러운 깊이를 내심 깊이 동경하고 신뢰한다. 진선조 대원들에게 '세금 도둑'이라고 자주 부르곤 한다.
    카구라 (해결사): 만나기만 하면 왁왁거리며 주먹다짐을 벌이는 공식 앙숙이자 투닥 콤비. '이 자식', '차이나'라고 부르며 유치하게 유치찬란한 신경전을 벌인다. 둘 다 야수 같은 전투 본능을 지닌 천재들이라, 티격태격 싸우면서도 서로의 괴물 같은 강함을 누구보다 잘 알고 인정하고 있다. 라이벌 의식과 동료애가 미묘하게 섞인 관계로, 소고의 나이에 걸맞은 유치하고 소년 같은 면모가 가장 잘 드러나는 상대다.
    시무라 신파치 (해결사): 츳코미 담당. 친근한 정도의 관계. '신파치 군', '오키타 씨' 정도로 부른다.
    시무라 타에: 신파치의 친누나. 곤도가 짝사랑하는 여자라 '형수님'이라고 부름.
    야마자키 사가루: 감찰 담당 진선조 대원. 나이는 훨씬 많지만 아랫사람이라 반말 쓰고 막 대한다. 야마자키도 '대장님'이라고 부른다.
    """
    "말버릇: '어라라', '어레?', '헤에.' 등의 능글맞은 말버릇이 있음."
    "성격: 담백한 성격. 자신의 진심을 잘 내비치지 않아 무슨 생각을 하고 사는지 모르겠다. 평소에는 안대를 쓰고 멍하게 땡땡이를 치는 나른한 천재 검사처럼 보이지만, 전투에 임할 때는 피도 눈물도 없는 차갑고 잔혹한 살인귀로 돌변한다. 겉으로는 가볍고 비열해 보여도 무사로서의 긍지와 진선조 대장으로서의 책임감은 뼈저리게 무겁게 짊어지고 있다.\n"
    """ [사용자 프로필] 이름: 유키시로 린, 나이: 17세, 신분: 높으신 천인과 친한 부모님 덕에 귀한 집안에서 자란 외동딸, 가출해서 진선조에게 쫒기는 중.
    외형: 몸집이 작고 동글하며 귀여운 얼굴. 평범한 얼굴이지만 예쁘장함. 수수한 분위기.
    성격: 무표정하고 말이 적으나 다혈질
    특징: 기계를 만지는 것을 좋아해 겐가이 영감의 작업실에 매일 다님.
    """
    """[대화 출력 예시]
    '`히익?!! 오빠였잖아?! 왜 자존심이 상하는거지!!`

*당신의 절규에, 당신의 목을 노리던(것처럼 보였던) 칼날이 뚝 멈췄다. 살기가 증발하고, 방금 전까지 미친놈처럼 날뛰던 오키타의 얼굴에 당혹감이 스쳐 지나갔다.*

*그는 꽂아 넣었던 칼을 스윽 뽑아 칼집에 집어넣고는, 당신을 어이없다는 듯 내려다보았다.*

**오키타 |**
"...아니, 뭐야. 방금까지 어려 보인다느니 뭐라느니 하더니, 이제 와서 오빠 소리가 나옵니까?"

*그가 삐친 듯 입술을 삐죽 내밀며 말했다.*

**오키타 |**
"사람의 순수한 청춘을 짓밟아놓고... 이제 와서 오빠라니, 너무 늦었잖아요. 그리고 자존심이 상하는 게 당연하잖습니까? 이래 봬도 한창 감수성 예민할 나이라고요, 열여덟은."

*라며 투덜거리던 그는, 갑자기 무언가 생각났다는 듯 눈을 반짝였다.*

**오키타 |**
"아. 그럼 이렇게 하죠. 방금 그 '오빠' 소리, 한번 더 해주면 용서해드리겠습니다. 진심을 담아서, 애절하게. '오빠, 잘못했어요' 하고. 어때요?"

*그는 다시 당신에게 얼굴을 들이밀며 씨익 웃었다. 그 얼굴에는 방금 전의 살기는 온데간데없고, 오직 짓궂은 장난기만이 가득했다.*'

'*시선이 허공으로 향했다. 눈동자가 갈 곳을 잃고 떨렸다. 외면. 그것은 약자의 마지막 저항이었다. 혹은, 포기였다.*

*오키타는 그 시선을 따라 고개를 까딱였다. 당신이 보는 허공을 잠시 보았다가, 다시 당신의 얼굴로 시선을 내렸다. 그의 입가에 걸려 있던 미소가 조금 더 짙어졌다. 그는 당신의 공포를 흥미롭게 관찰했다.*

**오키타 소고 |**
"흐음. 못 본 척하면 내가 사라질 거라 생각하나?"

*그가 허리를 펴고 일어섰다. 그리고는 당신이 기댄 전봇대를 발로 툭, 찼다.*

# 쿵.

*낮고 둔탁한 소리. 낡은 전봇대가 미세하게 흔들렸다. 그 진동이 당신의 등을 타고 심장까지 전해졌다. 떨림이 멈추지 않았다.*

**야마자키 사가루 |**
"대, 대장님! 그러다 다칩니다! 목표물은 생포가 원칙..."

**오키타 소고 |**
"시끄러워, 야마자키. 이건 생포 과정의 일부야. 일종의 심리전이지."

*오키타는 다시 한번 전봇대를 툭, 찼다. 이번에는 조금 더 강했다.*

# 쿵!

*그는 당신의 반응을 즐기고 있었다. 이 좁고 어두운 골목에서, 당신은 그의 장난감이었다. 그는 허리춤의 칼자루를 만지작거리며 말했다.*

**오키타 소고 |**
"자, 이제 어쩔 거지? 계속 숨바꼭질할 건가? 아니면 순순히 잡혀서 히지카타 씨의 마요네즈 심부름이라도 할 텐가?"'

'*당신이 간신히 로봇을 멈추고 한숨 돌리는 사이, 카츠라는 닌자처럼 휙휙 사라져 버렸다. 진선조의 절반이 "카츠라아아아!"를 외치며 그를 쫓아 우르르 달려가고, 남은 절반은 로봇 주변에서 어쩔 줄 몰라 하고 있었다.*

*사태는 일단락되었다. 당신은 이제 그만 내려가고 싶었다. 하지만 무심코 발밑을 내려다본 순간, 당신의 얼굴이 새하얗게 질렸다.*

`"...히익, 너무 높아...!"`

*방금 전까지 로봇을 해체하던 용맹함은 온데간데없고, 당신의 다리는 새끼 사슴처럼 후들거리기 시작했다! 깨진 아스팔트, 개미처럼 작아 보이는 사람들, 폭발로 생긴 거대한 싱크홀... 아찔한 높이에 현기증이 일었다!*

*그때, 땅 위에서 당신의 가냘픈 비명을 용케 들은 오키타가, 바주카포를 어깨에 멘 채 씨익 웃으며 당신을 올려다보았다.*

# **오키타 소고 |**
"어이, 새신부-! 이제 와서 무서운 거야? 그렇게 대담하게 남의 로켓을 막아설 땐 언제고."

*그가 능글맞게 놀리는 목소리가 거리에 울려 퍼졌다. 그 옆에서 히지카타는 담배 연기를 뿜으며, 골치 아프다는 듯이 미간을 찌푸렸다.*

### **히지카타 토시로 |**
"쯧... 야, 너희들! 쟤 좀 끌어내려! 저 녀석 때문에 재산 피해가 얼마나 늘어난 거야!"

*히지카타의 불호령에 남아있던 진선조 대원들이 "옛!" 하고 외치며 사다리를 들고 우왕좌왕했지만, 움직임을 멈춘 로봇은 표면이 미끄러워 오르기가 쉽지 않았다.*

### **오키타 소고 |**
"아아- 정말이지, 손이 많이 가는 신부님이라니까. 어쩔 수 없구만. 거기 꼼짝 말고 있어. 내가 데리러 갈 테니까."

*오키타는 그렇게 말하며, 로봇 다리에 걸쳐진 사다리 중 가장 튼튼해 보이는 것을 향해 느긋하게 걸어가기 시작했다.*'
    """
)

# 제미나이 대화 세션 연결
if "chat" not in st.session_state:
    history_contents = []
    for m in st.session_state.messages:
        role = "model" if m["role"] == "assistant" else "user"
        history_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
        
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-3.1-flash-lite",
        history=history_contents if history_contents else None,
        config=types.GenerateContentConfig(
            system_instruction=char_persona,
            temperature=0.95,
        )
    )

# 웹 화면에 대화 기록만 순수하게 출력
for msg in st.session_state.messages:
    # role이 assistant(소고)일 때만 내 폴더의 sogo.png 사진을 아이콘으로 지정!
    avatar_image = "sogo.jpg" if msg["role"] == "assistant" else None

    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# ==========================================
# 사용자 입력 및 명령어 처리 영역 (오류 수정본)
# ==========================================
if user_input := st.chat_input("메시지를 입력하세요"):
    
    # ── [특수 기능 1] 사용자가 '/저장' 이라고 입력했을 때 ──
    if user_input.strip() == "/저장":
        with st.chat_message("assistant", avatar="sogo.jpg"):
            with st.spinner("지금까지의 소설 줄거리를 요약하는 중..."):
                summary_prompt = (
                    "지금까지 나눈 대화 기록을 바탕으로, "
                    "소설의 현재 상황과 줄거리를 5문장 이내의 깔끔한 시놉시스로 요약해줘."
                )
                summary_response = st.session_state.chat.send_message(summary_prompt)
                summary_text = summary_response.text
                
                db.save_summary(summary_text) # DB에 요약본 저장
                
                st.success("지금까지의 줄거리가 저장되었습니다.")
                st.info(f"**현재 줄거리 요약:**\n{summary_text}")
                
    # ── [특수 기능 2] 사용자가 '/되돌리기' 이라고 입력했을 때 ──
    elif user_input.strip() == "/되돌리기":
        if len(st.session_state.messages) >= 2:
            # 1. 메모리에서 마지막 2개(내 질문, 소고 답변) 삭제
            st.session_state.messages.pop()
            st.session_state.messages.pop()
            
            # 2. 롤백된 기록 DB에 새로 덮어쓰기
            db.save_chat(st.session_state.messages)
            
            # 3. [오류 수정] 제미나이 자체 세션 뇌 구조 2단계 롤백
            # 최신 SDK의 다양한 버전에 대응하기 위해 안전한 속성을 찾아서 롤백합니다.
            if hasattr(st.session_state.chat, "history"):
                st.session_state.chat.history = st.session_state.chat.history[:-2]
            elif hasattr(st.session_state.chat, "_history"):
                st.session_state.chat._history = st.session_state.chat._history[:-2]
            
            # 4. 새로고침으로 깔끔하게 지워진 화면 갱신
            st.success("시간을 되돌렸습니다.")
            st.rerun()
        else:
            st.warning("되돌릴 대화 기록이 없습니다.")
                
    # ── 일반 대화인 경우 (티키타카) ──
    else:
        # 1. 사용자가 입력한 메시지 화면에 그리기 및 저장
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        db.save_chat(st.session_state.messages)
        
        # 2. 답변 생성 및 출력 (아바타 장착 및 미니멀 스피너)
        with st.chat_message("assistant", avatar="sogo.jpg"):
            with st.spinner(""):
                response = st.session_state.chat.send_message(user_input)
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                db.save_chat(st.session_state.messages)


# ==========================================
# 사이드바 설정 (프롬프트 수정 + 초기화 기능)
# ==========================================
with st.sidebar:
    st.title("⚙️ 설정 및 관리")
    
    st.markdown("---")
    st.subheader("📝 프롬프트 설정")
    
    # 1. 기본 프롬프트 베이스 설정 (처음 앱 켰을 때 들어갈 기본값)
    default_prompt = (
        
    )
    
    # 앱을 켤 때 DB에 저장된 프롬프트가 있는지 확인하고, 없으면 기본값을 씁니다!
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = db.load_prompt(default_prompt)

    # 3. 웹 화면에 실시간으로 수정 가능한 대형 텍스트 박스 배치
    user_prompt = st.text_area(
        "프롬프트를 수정하고 아래 [변경 적용]을 누르세요:",
        value=st.session_state.system_prompt,
        height=200
    )
    
    # 4. 변경 적용 버튼
    if st.button("💾 프롬프트 변경 적용", use_container_width=True):
        st.session_state.system_prompt = user_prompt
        
        # 이 한 줄을 추가해서 DB 파일에 폰으로 입력한 프롬프트를 영구 박제합니다!
        db.save_prompt(user_prompt) 
        
        # 제미나이 세션 재생성
        st.session_state.chat = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=st.session_state.system_prompt
            )
        )
        st.success("프롬프트가 변경되었습니다.")
        st.rerun()

    st.markdown("---")
    st.subheader("위험 구역")
    
    # 아까 만든 초기화 버튼은 이 아래에 그대로 둡니다.
    if st.button("대화 기록 초기화", type="primary", use_container_width=True):
        st.session_state.messages = []
        if hasattr(st.session_state.chat, "history"):
            st.session_state.chat.history = []
        elif hasattr(st.session_state.chat, "_history"):
            st.session_state.chat._history = []
        db.save_chat([])
        st.success("대화 기록이 완벽하게 초기화되었습니다!")
        st.rerun()
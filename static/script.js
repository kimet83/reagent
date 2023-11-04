
function logout() {
  fetch('/logout', {
    method: 'POST',
    credentials: 'same-origin' // 쿠키 포함을 허용하기 위해 설정
  })
    .then(response => {
      if (response.redirected) {
        // 로그아웃 후 리디렉션된 경우
        window.location.href = response.url; // 리디렉션된 페이지로 이동
      } else {
        // 로그아웃 실패 또는 오류 발생 시 동작
        // 필요한 에러 처리를 수행할 수 있습니다.
        console.error('로그아웃 실패');
      }
    })
    .catch(error => {
      console.error('오류 발생:', error);
    });
}

function change() {
  let selectedUser = document.getElementById("user").value;
  console.log("사용자 선택이 변경되었습니다. 선택된 사용자:", selectedUser);
  let formData = new FormData();
  formData.append("username", selectedUser);

  fetch('/change', { method: "POST", body: formData })
    .then((res) => res.json())
    .then((data) => {
      location.reload();
    });
}

function total() {
  window.open('/statistics', target = "_self")
}
function home() {
  window.open('/index', target = "_self")
}
function ref_reg() {
  window.open('/ref_reg', target = "_self")
}
function out_index() {
  window.open('/out_index', target = "_self")
}


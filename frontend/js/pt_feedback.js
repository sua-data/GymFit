(function () {
    const state = document.querySelector("#feedbackState");
    const list = document.querySelector("#feedbackList");

    let user = null;

    try {
        user = JSON.parse(
            sessionStorage.getItem("gymfitUser") || "null"
        );
    } catch {
        user = null;
    }

    const userId = Number(
        user?.user_id ?? user?.userId
    );

    if (!userId) {
        location.replace("/login");
        return;
    }

    if (user.account_type !== "MEMBER") {
        location.replace("/trainer/assignments");
        return;
    }

    async function load() {
        try {
            const response = await fetch(
                "/api/pt/feedback/member",
                {
                    headers: {
                        "X-User-Id": String(userId),
                    },
                }
            );

            const data = await response
                .json()
                .catch(() => null);

            if (!response.ok) {
                throw new Error(
                    data?.detail ||
                    "피드백을 불러오지 못했습니다."
                );
            }

            list.innerHTML = "";

            state.hidden = data.items.length > 0;
            list.hidden = !data.items.length;

            if (!data.items.length) {
                state.innerHTML =
                    "<strong>아직 등록된 피드백이 없어요.</strong>"
                    + "<p>운동을 완료하면 트레이너 피드백을 확인할 수 있어요.</p>";
                return;
            }

            data.items.forEach((item) => {
                const card = document.createElement("article");
                card.className =
                    "assignment-item feedback-item";

                const title = document.createElement("h3");
                title.textContent = item.assignment_title;

                card.append(title);

                const details = [
                    `${item.trainer_name} 트레이너 · ${item.exercise_name}`,
                    `완료 ${
                        item.completed_at
                            ? item.completed_at
                                .replace("T", " ")
                                .slice(0, 16)
                            : "-"
                    }`,
                    item.posture_score === null
                        ? "자세 점수 없음"
                        : `자세 점수 ${item.posture_score}점`,
                    item.content,
                    `작성 ${
                        item.created_at
                            .replace("T", " ")
                            .slice(0, 16)
                    }${
                        item.updated_at !== item.created_at
                            ? " · 수정됨"
                            : ""
                    }`,
                ];

                details.forEach((text) => {
                    const paragraph =
                        document.createElement("p");

                    paragraph.textContent = text;
                    card.append(paragraph);
                });

                if (item.image_url) {
                    const image =
                        document.createElement("img");

                    image.className =
                        "assignment-result-image";

                    image.src = item.image_url;
                    image.alt = "대표 자세 이미지";

                    card.insertBefore(
                        image,
                        card.children[3]
                    );
                }

                list.append(card);
            });
        } catch (error) {
            state.hidden = false;
            list.hidden = true;
            state.innerHTML =
                "<strong>피드백을 불러오지 못했어요.</strong>"
                + "<p>네트워크 연결을 확인한 뒤 다시 시도해 주세요.</p>";
            const retryButton = document.createElement("button");
            retryButton.type = "button";
            retryButton.className = "gymfit-state-action";
            retryButton.textContent = "다시 시도";
            retryButton.addEventListener("click", load);
            state.append(retryButton);
        }
    }

    load();
})();

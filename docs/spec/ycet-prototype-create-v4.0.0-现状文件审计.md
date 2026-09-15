# v4.0.0 现状文件审计

- 审计日期：2026-09-15
- 范围：`skill-outputs/ycet-prototype-create/` 全部 165 个文件。
- 方法：全部文件读取字节并计算 SHA-256；文本全量扫描，Python AST 提取结构，关键行为逐段核对。
- 边界：116 张历史 PNG 仅核对格式与尺寸，未逐张做视觉审查；缓存仅登记。未执行原型浏览器或功能测试。
- 运行状态文件仅登记路径、大小、摘要，不复制其中的令牌及日志内容。
- 配套方案：[优化执行方案](ycet-prototype-create-v4.0.0-执行方案.md)。

## 文件清单

| 路径 | 分类 | 字节数 | 读取信息 | SHA-256 |
| --- | --- | ---: | --- | --- |
| `.DS_Store` | 缓存／系统文件 | 6148 | 读取字节并登记，不作为需求依据 | `3d4d923719fd8a9d1368a36eb5871ef4474aa46eff88057f89752915161a9765` |
| `SKILL.md` | 源码／文档 | 8727 | 79 行 | `85e2086e3e71132f35bdd50bf15139eb4f04fa6758eee1558276081952930781` |
| `agents/openai.yaml` | 源码／文档 | 369 | 7 行 | `5a5dea77b55c8d14ec3fbfd2e924ef75473a28056d40b0cee2a3564fe262b940` |
| `assets/.DS_Store` | 缓存／系统文件 | 6148 | 读取字节并登记，不作为需求依据 | `84581df0373bc7503bf7a1c205bf3524658dcb3fbc572dbd9b83c838db098091` |
| `assets/frames/.ycet-editor/server.json` | 运行状态 | 356 | 9 行 | `834c6ed36d4971589424b874cfef02aa05100f49407985f981443f4e5761cdba` |
| `assets/frames/.ycet-editor/server.log` | 运行状态 | 63402 | 803 行 | `e14c681cca29463c6404f0ea30d535c25d22f4fd7e3134abf19a020313912699` |
| `assets/frames/.ycet-editor/workspace.json` | 运行状态 | 2450 | 82 行 | `d524767a6ab120ca861f04f68ad341ccf1d6ab605d80c97a05ea834bd622f4ef` |
| `assets/frames/README.md` | 源码／文档 | 3176 | 62 行 | `7f66136c54b83cafbc06019fd0cf08382521a75562000bf9447f0c38e9350747` |
| `assets/frames/android-pixel.html` | 源码／文档 | 6799 | 79 行 | `21e470c5eceb51aa2f1203ab4302e2655fdab982c8f6f12aba8296d106de293f` |
| `assets/frames/browser-chrome.html` | 源码／文档 | 6300 | 76 行 | `b330f9215e63cd85513e554d79a3f47cf324729ce65412d92e28450ef019e115` |
| `assets/frames/ipad-pro.html` | 源码／文档 | 6501 | 80 行 | `bf951de98a5220c5263e44b2a5778a8fd3a936ad86f70e958fbca55223bf6fbf` |
| `assets/frames/iphone-15-pro.html` | 源码／文档 | 7441 | 107 行 | `37d7742192976e880a017877b9f524c802ee4e58dcdba520a813b5a9ce656026` |
| `assets/frames/macbook.html` | 源码／文档 | 6410 | 77 行 | `f630f3387abc6cd07409f97df938e00a4b75d6553bc07f600d7d582e57e426b3` |
| `assets/frames/manifest.json` | 源码／文档 | 3598 | 98 行 | `ba40217068069ad99e755791cbac3481255602f125998ac53a03268d37f5a287` |
| `assets/workbench/app.js` | 源码／文档 | 90502 | 1834 行 | `4afe028099ee2aba6789c2b581a6d294be6e0f3d85ed33b151de1d5aff63261c` |
| `assets/workbench/icons.svg` | 源码／文档 | 3669 | 28 行 | `5f2400b549802d01480d5d670cd3bb1a08251c129d20d8ddf54e4836c93906b0` |
| `assets/workbench/index.html` | 源码／文档 | 18948 | 92 行 | `ddc1df08a432306c9663281fa3dadcdf4412e4d1813785dc657d20248da14b17` |
| `assets/workbench/preview-runtime.js` | 源码／文档 | 27229 | 658 行 | `e0ac67759828b4990be04d02cd83400af74246ca4884819cc27dfd80ee7c6a59` |
| `assets/workbench/styles.css` | 源码／文档 | 24318 | 258 行 | `49f170bbafa349fdae8366a98b959599de92e25d988122ed27a1fcba3cdaa206` |
| `docs/function-1-static-prototype.md` | 源码／文档 | 14385 | 224 行 | `64c4f70fcefcda7d0040a665d85851ed632d6af4ffcc091f8e26d20373764fa0` |
| `docs/function-2-precision-edit.md` | 源码／文档 | 5637 | 64 行 | `e29ccd617d406f3e833c5e42570ea24a23cede70ac781b579583a7f3583e4f19` |
| `docs/function-3-interactive-demo.md` | 源码／文档 | 13894 | 194 行 | `f33c5e01e372cfc0a7b39fc42112fa98737abead87d4b9de992d31f9decb29da` |
| `docs/function-4-existing-prototype-edit.md` | 源码／文档 | 21079 | 222 行 | `647338480745b3a7022c892121c930026cb62d3be1457e059f47361509480056` |
| `docs/function-5-mobile-single-file.md` | 源码／文档 | 11058 | 160 行 | `66dd61b4341c244b1d86b68e476e3c7b5fc406dd35078e7ea78dd4957e91677b` |
| `docs/shared-editlog-rules.md` | 源码／文档 | 3556 | 67 行 | `7f072dd62ec4cb93d75e87320aa19fa55b34ba8accb715e0be932c47b4f57cfe` |
| `docs/shared-prototype-standards.md` | 源码／文档 | 31914 | 507 行 | `17ed20807ddfe64f8d1ae5434ad5cb3c5cefa75400bf01a55cfcf67a21d1e587` |
| `docs/shared-workbench-protocol.md` | 源码／文档 | 19292 | 199 行 | `8f457c0547c4319715d1dc657fd6f34cfb8fc090faf96652843a28c16e9655c8` |
| `evals/evals.json` | 源码／文档 | 13267 | 203 行 | `fc64119abf4d0df5d6f6015c056799eb07259c5899bb9aedfa6bdf6bc53943b8` |
| `scripts/__pycache__/build_mobile_prototype.cpython-314.pyc` | 缓存／系统文件 | 75829 | 读取字节并登记，不作为需求依据 | `a03a5c10bee58b2bbbf6b87c65d7277921ccb95605b816127989afbaa41f816d` |
| `scripts/__pycache__/prototype_guard.cpython-314.pyc` | 缓存／系统文件 | 31586 | 读取字节并登记，不作为需求依据 | `a279eb8c284edad2cfe4ee21840295a08b796daeda48484e066eacc7eb681876` |
| `scripts/__pycache__/prototype_workbench.cpython-314.pyc` | 缓存／系统文件 | 117792 | 读取字节并登记，不作为需求依据 | `cdcdf27e4a0607a1dfeaeed936bb4da6e66299e765bcee608f3a990bbabb040f` |
| `scripts/__pycache__/release_audit.cpython-314.pyc` | 缓存／系统文件 | 5594 | 读取字节并登记，不作为需求依据 | `6a4fc06e142de876c963601ee4fc5cb54f75f20399c0adffc37ceddef694473e` |
| `scripts/__pycache__/test_build_mobile_prototype.cpython-314.pyc` | 缓存／系统文件 | 16600 | 读取字节并登记，不作为需求依据 | `a77eadae9b44adaa7852d3ce241eabde42068a905955a7d96f63e61238b2e986` |
| `scripts/__pycache__/test_mobile_prototype_runtime.cpython-314.pyc` | 缓存／系统文件 | 12986 | 读取字节并登记，不作为需求依据 | `f83b077a57b832a88733c4779468021f374ec01b8bb598af2e76c9a3d7af4201` |
| `scripts/__pycache__/test_prototype_guard.cpython-314.pyc` | 缓存／系统文件 | 8504 | 读取字节并登记，不作为需求依据 | `63d3f642251e05dcc9fe1a2c2adba66c45a11c1bbdb124058d2d25ead00b51ca` |
| `scripts/__pycache__/test_prototype_workbench.cpython-314.pyc` | 缓存／系统文件 | 98317 | 读取字节并登记，不作为需求依据 | `07d04ef3b82d06c155eb1c0e753c7ec150671d7b12043c37e2113387fec5cd52` |
| `scripts/__pycache__/test_workbench_runtime.cpython-314.pyc` | 缓存／系统文件 | 104880 | 读取字节并登记，不作为需求依据 | `44864d50212507ef9a0f5375fae9fd568e11bf2308dc189a5409e2dd0f9d7961` |
| `scripts/__pycache__/validate_skill.cpython-314.pyc` | 缓存／系统文件 | 27436 | 读取字节并登记，不作为需求依据 | `3127806bd6e7c398cd2606d97b4fb66a3bf1b7d02ce42033a023825bea6fd128` |
| `scripts/build_mobile_prototype.py` | 源码／文档 | 46993 | 990 行 | `f2b47957de4c73bfb314da3a7e3cfd7111557cbc7d2f2a9db2a93b822260de3f` |
| `scripts/prototype_guard.py` | 源码／文档 | 25002 | 575 行 | `9aad551a2dc30aa49c4fe95d5e0e06ab46458d3a16fa134a085e07415b21a5eb` |
| `scripts/prototype_workbench.py` | 源码／文档 | 73796 | 1512 行 | `9c1190d399b46014d6630e5026f0118a960a765d4df7cfbddfb4190551140c1e` |
| `scripts/release_audit.py` | 源码／文档 | 3499 | 88 行 | `368d3ca590cd19e97769c13bb0fc8e6a8f83e8107111d8df0f986793ea9f3cdf` |
| `scripts/test_build_mobile_prototype.py` | 源码／文档 | 11867 | 274 行 | `c9886896a4e7c79ef09eadb3b4f21f40b6eba00ad9e9a7d2ecf9d67dd512f4c0` |
| `scripts/test_frames_runtime.py` | 源码／文档 | 14172 | 324 行 | `67346e05f0abd46ca6acd19f778e3591be74903930789053ca8eeff7869c66aa` |
| `scripts/test_mobile_prototype_runtime.py` | 源码／文档 | 8349 | 179 行 | `840b870735f554382272e8e50e4500db492770b96c71bdef584ab30341fcfcb4` |
| `scripts/test_prototype_guard.py` | 源码／文档 | 10252 | 232 行 | `4309031e42c292815444a90d090cc233ce71da9db48ae4190e5d29356f1be9ec` |
| `scripts/test_prototype_workbench.py` | 源码／文档 | 49210 | 875 行 | `0a8531ba26f8c159dc982a023e8156ca297b32771bb0f045cb572ba0c32094bf` |
| `scripts/test_workbench_runtime.py` | 源码／文档 | 71909 | 1221 行 | `2fa7f32a6c63c2d32de5792437cff90bce4dd3b216335d804ace76a9fb4d4a68` |
| `scripts/validate_skill.py` | 源码／文档 | 23403 | 476 行 | `a746ee52504834b1cae847682e781d688a7a450f99d877844f282678c1dea493` |
| `test-artifacts/annotation-clear-after/annotation-edge-chrome.png` | 历史测试截图 | 114115 | 1440×900 | `05f0c8ae6c11e050ecf2853fdbda7f5fb1adf21f5398ef23c556ced35db01587` |
| `test-artifacts/annotation-clear-after/annotation-marker-chrome.png` | 历史测试截图 | 128745 | 1440×900 | `0e475d035763381113dfcda9e71d32a240f88f530bfb48f5afca2239fce40401` |
| `test-artifacts/annotation-clear-after/color-picker-chrome.png` | 历史测试截图 | 16835 | 292×411 | `02eeab9413ec6adcd4f5f22632661dce69daf3faacbffeb2db11525c292f52f1` |
| `test-artifacts/annotation-clear-after/sidebar-collapsed-chrome.png` | 历史测试截图 | 82150 | 1440×900 | `5e4d9433837a1e107108494a245133430d6de532e3c8ed091e3dcd12d22b0ba0` |
| `test-artifacts/annotation-clear-after/workbench-chrome.png` | 历史测试截图 | 102167 | 1440×900 | `a73d2aa7807d81c2dde54ae1816dec0a987e67db9db46e7009d8bfed63b8e9c7` |
| `test-artifacts/annotation-clear-after/workbench-edge.png` | 历史测试截图 | 101438 | 1440×900 | `2b1396cee15bdbf8f5268c1374918aa4cf3e886bf2a76720c3da5d37659d72ad` |
| `test-artifacts/annotation-clear-before/annotation-edge-chrome.png` | 历史测试截图 | 113426 | 1440×900 | `0beb42d81c0593e9a91e1b238ab4df2e5c31cde66049c68d6882d39feff78337` |
| `test-artifacts/annotation-clear-before/annotation-marker-chrome.png` | 历史测试截图 | 128735 | 1440×900 | `975f76aeb9c0aeafa819c72a058b5699e591fc0587c8d8390dbe36cf11fdbd13` |
| `test-artifacts/annotation-clear-before/color-picker-chrome.png` | 历史测试截图 | 16835 | 292×411 | `02eeab9413ec6adcd4f5f22632661dce69daf3faacbffeb2db11525c292f52f1` |
| `test-artifacts/annotation-clear-before/sidebar-collapsed-chrome.png` | 历史测试截图 | 82065 | 1440×900 | `f2aee193800a78a6dc5fe1a5bed8d3ed56eda84a904974decbf03ada4df03bc5` |
| `test-artifacts/annotation-clear-final/annotation-edge-chrome.png` | 历史测试截图 | 114047 | 1440×900 | `44fd5c0d61cfe2a3d8bb15cbd9b8da603fb377a99337abfea907501e922d0174` |
| `test-artifacts/annotation-clear-final/annotation-marker-chrome.png` | 历史测试截图 | 128685 | 1440×900 | `7861b47c385bd205edd9d8efdf5b3d20ad0c2d928bd15dbbba4bab64bf87ac0d` |
| `test-artifacts/annotation-clear-final/color-picker-chrome.png` | 历史测试截图 | 16835 | 292×411 | `02eeab9413ec6adcd4f5f22632661dce69daf3faacbffeb2db11525c292f52f1` |
| `test-artifacts/annotation-clear-final/sidebar-collapsed-chrome.png` | 历史测试截图 | 83174 | 1440×900 | `3697801b56a3ff16e4ee380149f77de3ec248e44896bfb6ac2da6d8e372493eb` |
| `test-artifacts/annotation-clear-final/workbench-chrome.png` | 历史测试截图 | 101176 | 1440×900 | `95532f37d86b1f844c39bc9b8a6f0ebb22a5f569f6d31e2a88d65b31a4517edd` |
| `test-artifacts/annotation-clear-final/workbench-edge.png` | 历史测试截图 | 101335 | 1440×900 | `4c415857de0a4879adfa3f529aec5ec19fc27ec48c7a9a48f883cd012782bff8` |
| `test-artifacts/annotation-position-after-fix/annotation-marker-chrome.png` | 历史测试截图 | 128560 | 1440×900 | `393ad8755e711c388be13ea295a414e2bfec8948d22d6d9713c5ec4bb14ad245` |
| `test-artifacts/annotation-position-after-fix/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-position-after-fix/sidebar-collapsed-chrome.png` | 历史测试截图 | 81800 | 1440×900 | `7036ca5cb810d9a9ab3f93a9ef09accdf7fb8cde54dc313d44a6fc85d2e68e6b` |
| `test-artifacts/annotation-position-after-fix/workbench-chrome.png` | 历史测试截图 | 105340 | 1440×900 | `809819525df8476477100c47ecc3d29403d41e544f811f6b8c6c62d7c1614ff8` |
| `test-artifacts/annotation-position-after-fix-2/annotation-marker-chrome.png` | 历史测试截图 | 128517 | 1440×900 | `fb688aabd5805e460e90d6b1806169352029a34de5340d4a6fa5615b2d667800` |
| `test-artifacts/annotation-position-after-fix-2/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-position-after-fix-2/sidebar-collapsed-chrome.png` | 历史测试截图 | 82025 | 1440×900 | `8e55b9f3f4f8f745d0220994cf10bc58d19c935d4d69245cc5dccefa43c6218e` |
| `test-artifacts/annotation-position-after-fix-2/workbench-chrome.png` | 历史测试截图 | 99673 | 1440×900 | `e717c24473cc6172554a2b662fcf1d3cf586ac7c961b659cdcb0bdd2c2a3b769` |
| `test-artifacts/annotation-position-after-fix-3/annotation-marker-chrome.png` | 历史测试截图 | 128555 | 1440×900 | `3529862a3296fffe79787c755bae8dd9662a8b9b02a6978c5fadb7572d095043` |
| `test-artifacts/annotation-position-after-fix-3/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-position-after-fix-3/sidebar-collapsed-chrome.png` | 历史测试截图 | 81518 | 1440×900 | `d381e131e83c38aecbf84dd20ad143b02e04cd5f07a720c272ddaef847131643` |
| `test-artifacts/annotation-position-after-fix-3/workbench-chrome.png` | 历史测试截图 | 99640 | 1440×900 | `e955e2c310ac40748db2d691d444c50bbd81477ec444873b524ca3ba38433487` |
| `test-artifacts/annotation-position-after-fix-3/workbench-edge.png` | 历史测试截图 | 99641 | 1440×900 | `b1dac91ed90d8f072316c9cc3925662babbd17d8a2ab2d2911b89f2384076c60` |
| `test-artifacts/annotation-position-before-fix/annotation-marker-chrome.png` | 历史测试截图 | 127722 | 1440×900 | `52be7b4e1beaffe5df50abfd0fbfa35ffa2b8dc9716716a8ae55d726c8c40d7c` |
| `test-artifacts/annotation-position-before-fix/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-position-before-fix/sidebar-collapsed-chrome.png` | 历史测试截图 | 82458 | 1440×900 | `a0918659de187b3a6d6b6393a09aa1b4121229e2bea763499e502726bb7f20ee` |
| `test-artifacts/annotation-position-before-fix-2/annotation-marker-chrome.png` | 历史测试截图 | 127670 | 1440×900 | `0e8200ad69f17d2f2672a2d873118c9351c9bd5d9ca3ad73d904ae44f6b81e03` |
| `test-artifacts/annotation-position-before-fix-2/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-position-before-fix-2/sidebar-collapsed-chrome.png` | 历史测试截图 | 80984 | 1440×900 | `7a60b93533eb5ef68ce6b828b1151ae97abfb7d1efa1366b7d9634e2fd96942f` |
| `test-artifacts/annotation-position-before-fix-3/annotation-marker-chrome.png` | 历史测试截图 | 127817 | 1440×900 | `7a5fecebf99dde7d7ab926b9a961ea39d94604ef65649668e9e235b41b43e941` |
| `test-artifacts/annotation-position-before-fix-3/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-position-before-fix-3/sidebar-collapsed-chrome.png` | 历史测试截图 | 81225 | 1440×900 | `26308ab94abcadb03e126b6752a6429971172c37dc1b49df13f3b6dc1a31f027` |
| `test-artifacts/annotation-position-before-fix-4/annotation-marker-chrome.png` | 历史测试截图 | 127765 | 1440×900 | `054d1415693c25f6c0fb4fd1a03c4fa7f75f19a7e66f5b3bb5b16b2c6a33d198` |
| `test-artifacts/annotation-position-before-fix-4/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-position-before-fix-4/sidebar-collapsed-chrome.png` | 历史测试截图 | 81223 | 1440×900 | `d2f6de6847939dcf40257092223389304fd627ecd4050c02b56321bcfeab946e` |
| `test-artifacts/annotation-position-final/annotation-edge-chrome.png` | 历史测试截图 | 113169 | 1440×900 | `380353d553ad7d25c516b01124545a9227665e082e4cc7f472ba82a301d23ab7` |
| `test-artifacts/annotation-position-final/annotation-marker-chrome.png` | 历史测试截图 | 128538 | 1440×900 | `4a1f74e88b37dd2127f1b3545b962618c2bb947b9bea3b1682a93452436969de` |
| `test-artifacts/annotation-position-final/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-position-final/sidebar-collapsed-chrome.png` | 历史测试截图 | 81828 | 1440×900 | `0c24d123608c55b66e1f49e5aa5b5139ac117ab83dd37317ed81c745aaef95d8` |
| `test-artifacts/annotation-position-final/workbench-chrome.png` | 历史测试截图 | 100245 | 1440×900 | `fe2fbcc8f97ec95c240b7d0ebffa34659ae111bc23b7a00e423fda084f166839` |
| `test-artifacts/annotation-position-final/workbench-edge.png` | 历史测试截图 | 100055 | 1440×900 | `2905bd1ed6f79d10a442a3e7a48bca4a9e7ef5e39bca5f1d4981284d6dd8ed9d` |
| `test-artifacts/annotation-sidebar-after-fix/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-sidebar-after-fix/workbench-chrome.png` | 历史测试截图 | 99550 | 1440×900 | `3fbe9f6e0bc10ee44e2afa0055d2f7b80c18be2b9a13cf17bae77a16fcb2a501` |
| `test-artifacts/annotation-sidebar-after-fix/workbench-edge.png` | 历史测试截图 | 99671 | 1440×900 | `5a52f9a5236568d81586450ba799847a7f46c3303a4fa03b44f597654f17b747` |
| `test-artifacts/annotation-sidebar-before-fix/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-sidebar-final/annotation-marker-chrome.png` | 历史测试截图 | 127781 | 1440×900 | `3485c2dee6ca1b34b52e8694da434244a78912df53729e48c6ed998603ebe602` |
| `test-artifacts/annotation-sidebar-final/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/annotation-sidebar-final/sidebar-collapsed-chrome.png` | 历史测试截图 | 82160 | 1440×900 | `62abcc95eab13b8687dc398c5e3e0a1abe60ab54840f60226432e96ceaf760e4` |
| `test-artifacts/annotation-sidebar-final/workbench-chrome.png` | 历史测试截图 | 100061 | 1440×900 | `9838b99d429f1f029cbd691b9dc8db7ad4681b1ab2d6c0f6c5e4b670ae49313d` |
| `test-artifacts/annotation-sidebar-final/workbench-edge.png` | 历史测试截图 | 100136 | 1440×900 | `c84ffb5d48a564728146869648ec949305c4b2e51a7a10be6ba27c2df5ae7cd1` |
| `test-artifacts/current/workbench-chrome.png` | 历史测试截图 | 101794 | 1440×900 | `5d0397e0ac09cefcfc919cbbcd734a00c78aa9674a3e54f9ce3fc386d806eaed` |
| `test-artifacts/current/workbench-edge.png` | 历史测试截图 | 100575 | 1440×900 | `8d869029d3912f0c7e1135c90771114ce9c393c60acf865c4dbd48691bce3141` |
| `test-artifacts/current-round-2/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/current-round-2/workbench-chrome.png` | 历史测试截图 | 102927 | 1440×900 | `b5901dc22660fdc096d5081185fda2ed20fb98906420e2cc6ad7f4f195b467e8` |
| `test-artifacts/current-round-2/workbench-edge.png` | 历史测试截图 | 102291 | 1440×900 | `0bc177ca4ab563451bb63920e269263b6ce67fecefbd483c22ef1258b8f9829b` |
| `test-artifacts/current-round-3/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/current-round-3/workbench-chrome.png` | 历史测试截图 | 98603 | 1440×900 | `00c5edb26e965ac1e933e12f95af12da125452c6b410d22a11e0db6c284a9a2c` |
| `test-artifacts/current-round-3/workbench-edge.png` | 历史测试截图 | 98464 | 1440×900 | `2231fc445c2597cb228adc75c564adbb56314b53cd3f1694d7ffa1bea449a083` |
| `test-artifacts/hover-scroll-after-fix/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/hover-scroll-after-fix/workbench-chrome.png` | 历史测试截图 | 99335 | 1440×900 | `a2c235697248fc3c5a9036272e0d587f5da2e3e6a41005d28e05062aa4645925` |
| `test-artifacts/hover-scroll-after-fix/workbench-edge.png` | 历史测试截图 | 99640 | 1440×900 | `d9aca964d8e29bac5f5324cce383d13bfaaa5db5834f78f4bba871ff816b945e` |
| `test-artifacts/hover-scroll-before-fix/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/refresh-icon-after/annotation-edge-chrome.png` | 历史测试截图 | 113425 | 1440×900 | `790844601b150e3e26f84ad8d9f6e0e7b1a95766c1632b00bedaab51bc3521c5` |
| `test-artifacts/refresh-icon-after/annotation-marker-chrome.png` | 历史测试截图 | 128732 | 1440×900 | `b28f69b9c154400bb5e49c88e9e9a5d70ca8628519ef7d20872f98bcad82199e` |
| `test-artifacts/refresh-icon-after/color-picker-chrome.png` | 历史测试截图 | 16835 | 292×411 | `02eeab9413ec6adcd4f5f22632661dce69daf3faacbffeb2db11525c292f52f1` |
| `test-artifacts/refresh-icon-after/sidebar-collapsed-chrome.png` | 历史测试截图 | 83451 | 1440×900 | `0448e32221b9bafd33e041f0cea489e8f2fae6667f49847fce8610db10e82c03` |
| `test-artifacts/refresh-icon-after/workbench-chrome.png` | 历史测试截图 | 100107 | 1440×900 | `e92d28276297df711f1672460a8617cdf97681c9c538a3392044154a14484c10` |
| `test-artifacts/refresh-icon-after/workbench-edge.png` | 历史测试截图 | 99807 | 1440×900 | `fdc93cafd8d2532cdaff757c2e208b49ef32d5754bf6ec6caee416c3fc496ffb` |
| `test-artifacts/refresh-icon-before/annotation-edge-chrome.png` | 历史测试截图 | 113187 | 1440×900 | `11b066932b56c83cfbc10c672d716f8b20267223c4bb7785fbd2035ad2a59348` |
| `test-artifacts/refresh-icon-before/annotation-marker-chrome.png` | 历史测试截图 | 128566 | 1440×900 | `f08537c3f8bb36b6aa05b91d19e428f382e063c00ae2ac3f73fd4113dd461bbb` |
| `test-artifacts/refresh-icon-before/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/refresh-icon-before/sidebar-collapsed-chrome.png` | 历史测试截图 | 81213 | 1440×900 | `1cc2a06c832f867db2911141ae2aaf05baa2e68f8bdf22b0a1057e0daa8d47a4` |
| `test-artifacts/result-color-after-fix/annotation-edge-chrome.png` | 历史测试截图 | 122274 | 1440×900 | `6d21a2aa073f0a40f3e5fb38ba29b9dc1a42029e315172cbb21356bcae89ade0` |
| `test-artifacts/result-color-after-fix/annotation-marker-chrome.png` | 历史测试截图 | 134169 | 1440×900 | `8ce215daaf7b9caa1fdc293b55b9dcbddbc27371fa36f4a3829511615fbdf721` |
| `test-artifacts/result-color-after-fix/color-picker-chrome.png` | 历史测试截图 | 20989 | 292×410 | `0a33ac219a07c15445326d7f0fb2f16984a4c86792c0674d940323533814e18d` |
| `test-artifacts/result-color-after-fix/result-dialog-chrome.png` | 历史测试截图 | 127803 | 1024×768 | `fab7f859ca98cdb55c2e9c08f4096a2adda0655e7e026981714c58a5adb83e51` |
| `test-artifacts/result-color-after-fix/sidebar-collapsed-chrome.png` | 历史测试截图 | 100030 | 1440×900 | `541c5359b9c34e7129947b58183706eace02783a7c99730429573292117443b2` |
| `test-artifacts/result-color-after-fix/workbench-chrome.png` | 历史测试截图 | 127409 | 1440×900 | `1823190df7bcb77aea957b15693348703b20b4f5d53005fdc6adc2873a3a9038` |
| `test-artifacts/result-color-after-fix/workbench-edge.png` | 历史测试截图 | 126960 | 1440×900 | `aacd7bf49af6c580577771f967d9eb35846f9d613186c56a9f526bb9d7c74ace` |
| `test-artifacts/result-color-before-fix/annotation-edge-chrome.png` | 历史测试截图 | 122363 | 1440×900 | `3c76d1648ca3000307710ff7c12683545b148fa4494ebf0cea268c8812709570` |
| `test-artifacts/result-color-before-fix/annotation-marker-chrome.png` | 历史测试截图 | 134263 | 1440×900 | `dd33cb79fcdb08dddc9d2474153eb2f5649b62c2ecb1def3bf843bdf1f009e27` |
| `test-artifacts/result-color-before-fix/color-picker-chrome.png` | 历史测试截图 | 20506 | 292×410 | `2f60ea2e65ddc5e66ad561cf32e7a219041abd5050fb90172848a5b94189db7f` |
| `test-artifacts/result-color-before-fix/result-dialog-chrome.png` | 历史测试截图 | 127909 | 1024×768 | `1f723249ffe4ef33250b902aa460c2a91d4d89e87a153e52702b98f78cddbb1d` |
| `test-artifacts/result-color-before-fix/sidebar-collapsed-chrome.png` | 历史测试截图 | 100370 | 1440×900 | `15ee794a68048f4fe468741ed736108df98d786270c2e80d43690c277587a21e` |
| `test-artifacts/result-dialog-after-fix/annotation-edge-chrome.png` | 历史测试截图 | 122228 | 1440×900 | `36d298eb1e07b5a7c0a8bbc64a0be17b5a79eb91700e622e2a652345e71274cc` |
| `test-artifacts/result-dialog-after-fix/annotation-marker-chrome.png` | 历史测试截图 | 134124 | 1440×900 | `9f92a612c5c43fa4e429ee7d06f199b06e96ba0f28b6804eeef9fb1579202743` |
| `test-artifacts/result-dialog-after-fix/color-picker-chrome.png` | 历史测试截图 | 20506 | 292×410 | `2f60ea2e65ddc5e66ad561cf32e7a219041abd5050fb90172848a5b94189db7f` |
| `test-artifacts/result-dialog-after-fix/sidebar-collapsed-chrome.png` | 历史测试截图 | 98711 | 1440×900 | `f9fa1822c07b7403509d593d1665a6e8060f240f98736d87025ea5966dc9f43a` |
| `test-artifacts/result-dialog-after-fix/workbench-chrome.png` | 历史测试截图 | 127011 | 1440×900 | `aa4081f52ba1debd0fdf3a5b4ce6fcd199a5d1c4372e9c3df0ded568bb01ee68` |
| `test-artifacts/result-dialog-after-fix/workbench-edge.png` | 历史测试截图 | 126816 | 1440×900 | `03c191b5a1bba0872aa1c98fd26bc2da47ffa0f4ece46bde663d2d22d2d73e9e` |
| `test-artifacts/result-dialog-before-fix/annotation-edge-chrome.png` | 历史测试截图 | 122504 | 1440×900 | `55a1c5170023e298de905e0c95789ce73e667a75b8c874cd040413ab949292f5` |
| `test-artifacts/result-dialog-before-fix/annotation-marker-chrome.png` | 历史测试截图 | 134407 | 1440×900 | `8cb8af46cfecdb99b893e8d3469685a776b30d22247935e9c288292bce10f563` |
| `test-artifacts/result-dialog-before-fix/color-picker-chrome.png` | 历史测试截图 | 20506 | 292×410 | `2f60ea2e65ddc5e66ad561cf32e7a219041abd5050fb90172848a5b94189db7f` |
| `test-artifacts/result-dialog-before-fix/sidebar-collapsed-chrome.png` | 历史测试截图 | 98923 | 1440×900 | `cdfa4b7b25df0f9cad4dd583dff5eeae539a8619d8d5a0a9be23973ed03effa2` |
| `test-artifacts/scaled-iframe-regression-green/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/scaled-iframe-regression-green/workbench-chrome.png` | 历史测试截图 | 99742 | 1440×900 | `75c2425b113c2952776992c3724afd029181fccb44c94d07bb4ba6c337f38dc4` |
| `test-artifacts/scaled-iframe-regression-green/workbench-edge.png` | 历史测试截图 | 100012 | 1440×900 | `7f9c62475f3d722019cd52a5bb1555ed2770ff366e04179c75d81036dcf2eabe` |
| `test-artifacts/scaled-iframe-regression-red/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/sync-pages-current/annotation-edge-chrome.png` | 历史测试截图 | 122443 | 1440×900 | `7a032d7c160cdc9484ab1129d1348060c11b12d5c59574206ada6ca5b6488a89` |
| `test-artifacts/sync-pages-current/annotation-marker-chrome.png` | 历史测试截图 | 134343 | 1440×900 | `06b210fcdfcb4ba460ac01a5e6598341f2155196696a7f547cd3262791201de0` |
| `test-artifacts/sync-pages-current/color-picker-chrome.png` | 历史测试截图 | 20506 | 292×410 | `2f60ea2e65ddc5e66ad561cf32e7a219041abd5050fb90172848a5b94189db7f` |
| `test-artifacts/sync-pages-current/sidebar-collapsed-chrome.png` | 历史测试截图 | 98969 | 1440×900 | `1d16db58dd5111762c5d22d0313071b56f6c713ab12d0031e956e44257773100` |
| `test-artifacts/sync-pages-current/workbench-chrome.png` | 历史测试截图 | 127197 | 1440×900 | `25583c559d356dc6b20932af38fd411d51a7f7b28d8e469149171a52e3e04cfa` |
| `test-artifacts/sync-pages-current/workbench-edge.png` | 历史测试截图 | 127026 | 1440×900 | `5459ce37c8984662febdbe8b496ec854ab76cc2ca27cd0d9be0c4a16691a2950` |
| `test-artifacts/tooltip-after-fix/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/tooltip-after-fix/workbench-chrome.png` | 历史测试截图 | 99472 | 1440×900 | `bcf33231f654af090999c1cebb69b0570475d44fb97be23942b420802c615d69` |
| `test-artifacts/tooltip-after-fix/workbench-edge.png` | 历史测试截图 | 99095 | 1440×900 | `8056da40443b60fe049105354bf290858c99251bc56744451759572ef51fa20b` |
| `test-artifacts/tooltip-before-fix/color-picker-chrome.png` | 历史测试截图 | 16812 | 292×411 | `bccf7d38ed4933a9318af76a8472c565dda24b665c02be02402405dc38992615` |
| `test-artifacts/workbench-chrome.png` | 历史测试截图 | 96596 | 1440×900 | `2a3c2c67a6b6053ea22e3b9d82d238953ccc865f13b579e3b43a4e591279bab0` |
| `test-artifacts/workbench-edge.png` | 历史测试截图 | 96152 | 1440×900 | `4c691ab54b147705f36a962b580e6c9955e545166dbb4825716a59b99d57c8f7` |

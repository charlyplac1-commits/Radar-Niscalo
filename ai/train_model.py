import json, os, shutil
from pathlib import Path
import torch
from torch import nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms, models

ROOT=Path(os.environ.get("DATASET_DIR","ai_dataset"))
OUT=Path("models/niscalo-detector"); OUT.mkdir(parents=True,exist_ok=True)
WORK=Path("/tmp/niscalo_train"); shutil.rmtree(WORK,ignore_errors=True); WORK.mkdir(parents=True)
for cls in ("no_niscalo","niscalo"):
    d=WORK/cls; d.mkdir()
    src=ROOT/"negative" if cls=="no_niscalo" else ROOT/"positive"
    for p in src.iterdir():
        if p.suffix.lower() in (".jpg",".jpeg",".png",".webp"): shutil.copy2(p,d/p.name)

train_tf=transforms.Compose([
    transforms.Resize((256,256)),transforms.RandomResizedCrop(224,scale=(.65,1.0)),
    transforms.RandomHorizontalFlip(),transforms.ColorJitter(brightness=.2,contrast=.2,saturation=.2,hue=.04),
    transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])
])
val_tf=transforms.Compose([
    transforms.Resize((224,224)),transforms.CenterCrop(224),transforms.ToTensor(),
    transforms.Normalize([.485,.456,.406],[.229,.224,.225])
])
base=datasets.ImageFolder(WORK,transform=train_tf)
nval=max(1,int(len(base)*.2)); ntrain=len(base)-nval
train_ds,val_split=random_split(base,[ntrain,nval],generator=torch.Generator().manual_seed(42))
val_base=datasets.ImageFolder(WORK,transform=val_tf)
val_ds=torch.utils.data.Subset(val_base,val_split.indices)
train=DataLoader(train_ds,batch_size=32,shuffle=True,num_workers=2)
val=DataLoader(val_ds,batch_size=32,shuffle=False,num_workers=2)

device="cuda" if torch.cuda.is_available() else "cpu"
model=models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
model.classifier[-1]=nn.Linear(model.classifier[-1].in_features,2)
model.to(device)
opt=torch.optim.AdamW(model.parameters(),lr=2e-4,weight_decay=1e-4)
lossfn=nn.CrossEntropyLoss(); best=0.0

for epoch in range(6):
    model.train(); total_loss=0
    for x,y in train:
        x,y=x.to(device),y.to(device); opt.zero_grad()
        loss=lossfn(model(x),y); loss.backward(); opt.step(); total_loss+=loss.item()*len(y)
    model.eval(); ok=tot=0
    with torch.no_grad():
        for x,y in val:
            z=model(x.to(device)); ok+=(z.argmax(1).cpu()==y).sum().item(); tot+=len(y)
    acc=ok/max(1,tot); print(f"epoch {epoch+1}/6 loss {total_loss/max(1,ntrain):.4f} val_acc {acc:.3f}")
    if acc>=best: best=acc; torch.save(model.state_dict(),OUT/"weights.pt")

model.load_state_dict(torch.load(OUT/"weights.pt",map_location=device)); model.eval().cpu()
dummy=torch.randn(1,3,224,224)
torch.onnx.export(model,dummy,OUT/"model.onnx",input_names=["images"],output_names=["logits"],dynamic_axes={"images":{0:"batch"},"logits":{0:"batch"}},opset_version=17)
info={"classes":base.classes,"positive_class":"niscalo","input_size":224,"normalization":{"mean":[.485,.456,.406],"std":[.229,.224,.225]},"validation_accuracy":round(best,4),"model":"MobileNetV3-Small","purpose":"experimental visual candidate detector; not species confirmation"}
(OUT/"model_info.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(info,ensure_ascii=False))
